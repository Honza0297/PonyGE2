"""
In every behavior, only setup and update methods are important.
setup: setup basic things needed for the behavior.
update: performed every time a behavior is ticked (activated).
"""
from __future__ import annotations

from typing import Optional, List, Tuple
from typing import TYPE_CHECKING

import py_trees
from py_trees.composites import Sequence, Selector
import random

from swarm.math import *
from swarm.models import TileModel
from swarm.types import ObjectType, Direction
from py_trees.decorators import Inverter

if TYPE_CHECKING:
    from swarm.agent import EvoAgent

class IsVisitedBefore(py_trees.behaviour.Behaviour):
    """
    Checks if agent's memory contains object of given type (not particular object).
    """
    def __init__(self, name):
        super(IsVisitedBefore, self).__init__(name)
        self.agent = None
        self.item_type = None

    def setup(self, agent, item=None, item_type=None) -> None:
        self.agent = agent
        self.item_type = item_type if item_type else item.type
        self.logger = agent.logger


    def initialise(self):
        pass

    def update(self):

        status = py_trees.common.Status.FAILURE

        if self.agent.places_visited[self.item_type]:
            status = py_trees.common.Status.SUCCESS

        return status

    def terminate(self, new_status):
        pass


class ObjectAtDist(py_trees.behaviour.Behaviour):
    """
    Checks if there are objects of the given type in the given distance.
    If dist = 1, then the agent is able to pick up the object.
    """
    def __init__(self, name):
        super(ObjectAtDist, self).__init__(name)
        self.distance = None
        self.item_type = None
        self.agent: Optional[EvoAgent] = None

    def setup(self, agent: EvoAgent, item=None, item_type=None, dist=1) -> None:
        self.agent = agent
        if isinstance(item_type, str):
            self.item_type = ObjectType.str2enum(item_type)
        else:
            self.item_type = item_type
        self.distance = dist
        self.logger = agent.logger

    def initialise(self) -> None:
        pass
    
    def _search_neighbourhood(self) -> Tuple[py_trees.common.Status, List]:
        """
        Search agent's neighbourhood. If the object is found, return SUCCESS and the list of objects.
        """
        status = py_trees.common.Status.FAILURE
        objects = []
        
        if not self.agent.neighbourhood.valid:
            self.logger.debug("running, neighbourhood not valid -> waiting to the next iteration")
            status = py_trees.common.Status.RUNNING
        elif not self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][self.agent.neighbourhood.center[1]]:
            pass  # NOTE Sometimes, center is None, could not reproduce in approx. 12k runs though...
        if self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][self.agent.neighbourhood.center[1]].position != tuple(self.agent.position):
            raise RuntimeError("Center position in neighbourhood {} differs from agent position {}".format(
                self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][
                    self.agent.neighbourhood.center[1]].position, self.agent.position))

        objects = self.agent.neighbourhood.get_objects(object_type=self.item_type, max_distance=self.distance)
        return status, objects
    
    def _search_local_map(self) -> Tuple[py_trees.common.Status, List]:
        status = py_trees.common.Status.FAILURE
        objects = []
        for row in self.agent.local_map:
            for tile in row:
                if tile and tile.occupied and tile.type == self.item_type:
                    objects.append((tile, compute_distance(self.agent.position, tile.position)))
        
        return status, objects
    
    def update(self) -> py_trees.common.Status:
        status = py_trees.common.Status.FAILURE
        
        objects = self._search_neighbourhood()
        if not objects:
            objects = self._search_local_map()
        if not objects:
            self.logger.debug(f"FAILURE, no object of type {self.item_type.value} in distance={self.distance}")
        else:
            status = py_trees.common.Status.SUCCESS
            self.logger.debug("SUCCESS, there {} object{} of type {} in distance={}".format(
                "are" if len(objects) > 1 else "is", "s" if len(objects) > 1 else "",
                self.item_type.value, self.distance))
            self.agent.objects_of_interest[self.item_type] = objects

        return status

    def terminate(self, new_state):
        pass


class RandomWalk(py_trees.behaviour.Behaviour):
    """
    Prepare the intention to move in a random direction.
    Direction is updated with prob = self.change_prob
    """
    def __init__(self, name):
        super(RandomWalk, self).__init__(name)
        self.blackboard = None
        self.change_prob = None
        self.agent = None
        self.last_time_failed = False

    def setup(self, agent, item=None, item_type=None, change_prob=25):
        self.agent = agent
        self.change_prob = change_prob  # percent

    def initialise(self):
        pass

    def update(self):
        change_direction = random.randint(1, 100)
        if change_direction <= self.change_prob or self.last_time_failed:  # with prob = self.change_prob, change direction of random walk
            self.agent.heading = random.choice((Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT))

        # set goal as the farthest tile in direct sight (not occupied) in the desired direction
        tmp_tile = self.agent.neighbourhood.get_next_tile_in_dir(self.agent.neighbourhood.center, self.agent.heading)
        while tmp_tile and not tmp_tile.occupied:
            tmp_tile = self.agent.neighbourhood.get_next_tile_in_dir(
                self.agent.neighbourhood.get_relative_pos(tmp_tile.position), self.agent.heading)

        if tmp_tile:  # goal found (i.e. the path is clear)
            self.last_time_failed = False
            self.agent.goal = tmp_tile
            status = py_trees.common.Status.SUCCESS
        else:  # cannot go in desired direction
            self.agent.goal = None
            self.last_time_failed = True
            status = py_trees.common.Status.FAILURE

        return status

    def terminate(self, new_status):
        pass

class SetNextStep(py_trees.behaviour.Behaviour):
    """
    Computes next position based on current goal
    TODO: currently, no speed is implemented (resp. speed is 1 tile per tick)
    
    NOTE: Broad heading is used when direct heading is not possible (obstacle in the way...).
        # Specifically, it is the main heading (for example UP) and the two adjacent headings (LEFT, RIGHT).
    """
    def __init__(self, name):
        super(SetNextStep, self).__init__(name)
        self.towards = None
        self.agent = None

    def setup(self, agent: EvoAgent, item=None, item_type=None, towards=True):
        self.agent = agent
        self.towards = towards
        self.logger = agent.logger

    def initialise(self):
        pass
    
    def _remove_invalid_headings(self):
        """
        Remove invalid headings from the list of candidate headings.
        """
        heading = []
        if not isinstance(self.agent.heading, (tuple, list)):
            self.agent.heading = [self.agent.heading]
        for direction in self.agent.heading:
            candidate_pos = pos_from_heading(self.agent.position, direction)
            # Dimension check
            if candidate_pos[0] < 0 or candidate_pos[1] < 0 or candidate_pos[0] >= self.agent.backend.board_model.dimension or candidate_pos[1] >= self.agent.backend.board_model.dimension:
                continue
            # occupancy check
            elif self.agent.neighbourhood.get_next_tile_in_dir(self.agent.neighbourhood.center, direction).occupied:
                continue
            else:
                heading.append(direction)

        return heading

    def _next_step_from_broad_heading(self) -> py_trees.common.Status:
        """
        If broad heading is used, the next step is the closest tile in the broad heading.
        """
        heading_and_distance = []
        for h in self.agent.heading:
            new_tile = self.agent.neighbourhood.get_next_tile_in_dir(self.agent.neighbourhood.center, h)
            dist = compute_distance(new_tile.position, self.agent.goal.position)
            heading_and_distance.append((h, dist))
        heading_and_distance.sort(key=lambda x: x[1])
        self.agent.heading = heading_and_distance[0][0]
        self.agent.next_step = pos_from_heading(self.agent.position, self.agent.heading)
        return py_trees.common.Status.SUCCESS
    
    def update(self) -> py_trees.common.Status:
        status = py_trees.common.Status.FAILURE
        self.agent.next_step = self.agent.position

        if self.agent.goal:
            goal = self.agent.goal
            self.agent.heading = heading_from_pos(self.agent.position, goal.position, towards=self.towards)
        else:
            self.logger.warning("No goal set, not moving")
            return status

        if isinstance(self.agent.heading, list):  # broad heading
            self.agent.heading = self._remove_invalid_headings(self.agent)
            status = self._next_step_from_broad_heading()
        else: # normal heading
            # If direct heading not possible (obstacle), use broad heading
            if not self._remove_invalid_headings(self.agent):
                self.agent.heading = Direction.broad_direction(self.agent.heading)
                self.agent.heading = self._remove_invalid_headings(self.agent)
                status = self._next_step_from_broad_heading()
            else: # direct heading possible
                self.agent.next_step = pos_from_heading(self.agent.position, self.agent.heading)
                status = py_trees.common.Status.SUCCESS
        return status

    def terminate(self, new_status):
        pass

class Move(py_trees.behaviour.Behaviour):
    """
    Actually move the agent according to the agent.next_step set elsewhere.
    """

    def __init__(self, name):
        super(Move, self).__init__(name)
        self.blackboard = None
        self.running = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.running = False
        self.logger = agent.logger

    def initialise(self):
        pass

    def update(self):
        if not self.agent.next_step:
            status = py_trees.common.Status.FAILURE
        elif tuple(self.agent.position) == tuple(self.agent.next_step):
            self.logger.debug(
                f"SUCCESS, {self.agent.name} is already at next step {self.agent.next_step}")
            self.agent.next_step = None
            self.agent.goal = None
            status = py_trees.common.Status.SUCCESS
        elif self.agent.goal.occupied and self.agent.goal.type in (ObjectType.FOOD, ObjectType.HUB) and \
            compute_distance(tuple(self.agent.position), tuple(self.agent.next_step)) == 1:  # next to food or hub
            #print(f"SUCCESS, {self.agent.name} is already next to {self.agent.goal.type}")
            self.logger.debug(
                f"SUCCESS, {self.agent.name} is already next to {self.agent.goal.type}")
            self.agent.next_step = None
            self.agent.goal = None
            status = py_trees.common.Status.SUCCESS
        else:
            resp = self.agent.backend.move_agent(self.agent, self.agent.position, self.agent.next_step)
            if resp and list(resp.position) == list(self.agent.next_step):
                # self.agent.position = resp.position
                self.logger.debug(
                    "SUCCESS, {} got response corresponding to its next_step={}".format(self.agent.name,
                                                                                        self.agent.next_step))
                self.agent.set_position(resp.position)
                self.agent.neighbourhood.valid = False  # we have moved -> neighbourhood is invalid
                status = py_trees.common.Status.SUCCESS
            else:
                self.logger.debug(
                    "FAILURE, resp.position = {} and agent's next step = {} not the same".format(resp.position,
                                                                                                 self.agent.next_step))
                status = py_trees.common.Status.FAILURE

        return status

    def terminate(self, new_status):
        pass


class IsCarrying(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(IsCarrying, self).__init__(name)
        self.quantity = None
        self.item_type = None
        self.agent = None

    def setup(self, agent: EvoAgent, item=None, item_type=None, quantity=1):
        self.agent = agent
        self.item_type = item_type
        self.quantity = quantity
        self.logger = agent.logger

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        for item in self.agent.inventory:
            if item.type == self.item_type:
                self.logger.debug(f"SUCCESS, item of type {self.item_type} found in inventory")
                status = py_trees.common.Status.SUCCESS
                break
        if self.agent.dropping_item == self.item_type:  # when in the middle of dropping
            self.logger.debug(f"SUCCESS, item of type {self.item_type} is the item to be dropped")
            status = py_trees.common.Status.SUCCESS
        return status

    def terminate(self, new_status):
        pass


class CanCarry(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(CanCarry, self).__init__(name)
        self.agent = None
        self.blackboard = None
        self.item_type = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = None
        self.logger = agent.logger

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE  # TODO change once items can be non carryable
        if self.item_type == ObjectType.FOOD:
            status = py_trees.common.Status.SUCCESS
            self.logger.debug("SUCCESS, food is carryable")
        else:
            self.logger.debug("FAILURE, item is not carryable (item is not food)")
        return status

    def terminate(self, new_status):
        pass


class IsDroppable(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(IsDroppable, self).__init__(name)
        self.item_type = None
        self.agent = None

    def setup(self, agent: EvoAgent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type
        self.logger = agent.logger

    def initialise(self):
        pass

    def update(self):
        # TODO once items start to be non-droppable, implement here
        self.logger.debug("SUCCESS, everything is droppable :)")
        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        pass


class PickUp(py_trees.behaviour.Behaviour):
    """
    Pick up an object of a given type from distance 1.
    Currently, only food can be picked up.
    """
    def __init__(self, name):
        super(PickUp, self).__init__(name)
        #self.blackboard = None
        self.running = None
        self.agent = None

    def setup(self, agent: EvoAgent, item=None, item_type=None):
        #self.running = False
        self.agent = agent
        if item:
            self.item_type = item.type
        else:
            self.item_type = item_type

    def initialise(self):
        pass

    def update(self):
        neighbour_objects = self.agent.neighbourhood.get_objects(self.item_type, 1)
        if neighbour_objects:
            item = random.choice(neighbour_objects)[0]  # item to pick
            try:
                pickup_status = self.agent.pickUpReq(item.position)
                if pickup_status:
                    self.running = False
                    self.logger.debug(f"SUCCESS, {self.agent.name} picked up an object")
                    status = py_trees.common.Status.SUCCESS
                else:
                    self.running = True
                    self.logger.debug("RUNNING, waiting for pickup response.")
                    status = py_trees.common.Status.RUNNING
            except TimeoutError:
                self.logger.debug("FAILURE, item not given")
                status = py_trees.common.Status.FAILURE
            except TypeError:
                self.logger.debug("FAILURE, got response of another type")
                status = py_trees.common.Status.FAILURE

        else:
            self.logger.debug("FAILURE, no goalObject present")
            status = py_trees.common.Status.FAILURE

        return status

    def terminate(self, new_status):
        pass


class Drop(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(Drop, self).__init__(name)
        self.agent = None
        self.item_type = None
        self.running = None

    def setup(self, agent: EvoAgent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type
        self.running = False
        self.logger = agent.logger

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        if not self.running:
            try:
                drop_status = self.agent.dropReq(self.item_type)
                if drop_status:
                    self.running = False
                    self.logger.debug("SUCCESS, item dropped")
                    status = py_trees.common.Status.SUCCESS
                else:  # drop not possible
                    self.logger.debug("FAILURE, drop is not possible (no space around etc.)")
                    status = py_trees.common.Status.FAILURE
            except TypeError:
                self.logger.debug("FAILURE, got response of different type")
                status = py_trees.common.Status.FAILURE

        # self.logger.debug("Returning status {}".format(status))
        return status

    def terminate(self, new_status):
        pass


class CanDrop(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(CanDrop, self).__init__(name)
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        tiles_next_to = [
            self.agent.neighbourhood.neighbourhood[self.agent.sense_radius + 1][self.agent.sense_radius + 1],
            self.agent.neighbourhood.neighbourhood[self.agent.sense_radius + 1][self.agent.sense_radius - 1],
            self.agent.neighbourhood.neighbourhood[self.agent.sense_radius - 1][self.agent.sense_radius + 1],
            self.agent.neighbourhood.neighbourhood[self.agent.sense_radius - 1][self.agent.sense_radius - 1]
        ]
        for tile in tiles_next_to:
            if tile and ((not tile.occupied) or tile.object.type == ObjectType.HUB):
                self.logger.debug("SUCCESS, can drop somewhere")
                status = py_trees.common.Status.SUCCESS
        if status == py_trees.common.Status.FAILURE:
            self.logger.debug("FAILURE, cannot drop item")
        return status

    def terminate(self, new_status):
        pass


class SetGoal(py_trees.behaviour.Behaviour):
    """
    Sets self.agent.goal based on objects of interest
    """
    def __init__(self, name):
        """Initialize."""
        super(SetGoal, self).__init__(name)
        self.agent = None
        self.item_type: ObjectType = ObjectType.GENERIC

    def setup(self, agent: EvoAgent, item=None, item_type=ObjectType.GENERIC):
        """Setup."""
        self.agent = agent
        self.item_type = item_type
        self.logger = agent.logger

    def initialise(self):
        """Pass."""
        pass

    def update(self):
        """Nothing much to do."""
        status = py_trees.common.Status.FAILURE
        if self.item_type not in self.agent.objects_of_interest.keys() or not self.agent.objects_of_interest[self.item_type]:
            return status
        else:
            closest_objects = [(None, len(self.agent.local_map))]
            for obj in self.agent.objects_of_interest[self.item_type]:
                if obj[1] == closest_objects[0][1]:
                    closest_objects.append(obj)
                elif obj[1] < closest_objects[0][1]:
                    closest_objects = [obj]
                else:
                    continue
            if closest_objects[0][0]:
                status = py_trees.common.Status.SUCCESS
                new_goal = random.choice(closest_objects)
                self.agent.goal = new_goal

        return status

###
# Composite non PPA behaviors
###

class GoTo(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(GoTo, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        set_goal = SetGoal("GT_set_goal")
        set_goal.setup(self.agent, item_type=self.item_type)

        set_next_step = SetNextStep("GT_setnextstep")
        set_next_step.setup(self.agent, item_type=self.item_type)
        move = Move("GT_move")
        move.setup(self.agent)

        # If we planned move and failed, we should consider setting new plan -> memory = False
        sequence = Sequence("GT_sequence", memory=False)
        sequence.add_children([set_goal, set_next_step, move])
        self.bt = py_trees.trees.BehaviourTree(root=sequence)

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class GoAway(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(GoAway, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        set_goal = SetGoal("GA_set_goal")
        set_goal.setup(self.agent, item_type=self.item_type)
        set_next_step = SetNextStep("GA_setnextstep")
        set_next_step.setup(self.agent, item_type=self.item_type, towards=False)
        move = Move("GA_move")
        move.setup(self.agent)

        # If we planned move and failed, we should consider setting new plan -> memory = False
        sequence = Sequence("GA_sequence", memory=False)
        sequence.add_children([set_goal, set_next_step, move])
        self.bt = py_trees.trees.BehaviourTree(root=sequence)

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


###
# PPA BEHAVIORS
###

class PPARandomWalk(py_trees.behaviour.Behaviour): 
    def __init__(self, name):
        super(PPARandomWalk, self).__init__(name)
        self.bt = None

    def setup(self, agent, item=None, item_type=None):
        rw = RandomWalk(name="PPA_random_walk_random_walk")
        rw.setup(agent, item, item_type)
        sns = SetNextStep(name="PPA_random_walk_next_step")
        sns.setup(agent)

        move = Move(name="PPA_random_walk_move")
        move.setup(agent)

        sequence = Sequence(name="PPA_random_walk_sequence", memory=True)
        sequence.add_children([rw, sns, move])

        self.bt = py_trees.trees.BehaviourTree(root=sequence)

    def initialise(self):
        pass

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class PPADrop(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPADrop, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

        selector = Selector(name="DRP_selector", memory=True)
        # postcondition
        already_carrying = IsCarrying(name="DRP_already_carrying")
        already_carrying.setup(self.agent, item_type=self.item_type,
                               quantity=1)
        is_dropped = Inverter(name="DRP_is_dropped", child=already_carrying)  # if no items to drop, consider it a sucess (?)

        sequence = Sequence(name="DRP_sequence", memory=True)

        is_droppable = IsDroppable(name="DRP_is_droppable")
        is_droppable.setup(agent, item_type=item_type)

        can_drop = CanDrop(name="DRP_canDrop")
        can_drop.setup(agent, item_type=item_type)

        actually_drop = Drop(name="DRP_actually_drop")
        actually_drop.setup(agent, item_type=item_type)

        sequence.add_children([is_droppable, actually_drop])
        selector.add_children([is_dropped, sequence])

        self.bt = py_trees.trees.BehaviourTree(root=selector)

    def initialise(self):
        pass

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class PPAPickUp(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPAPickUp, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

        selector = Selector(name="PU_selector", memory=True)
        # postcondition
        already_carrying = IsCarrying(name="PU_already_carrying")
        already_carrying.setup(self.agent, item_type=self.item_type, quantity=1)

        sequence = Sequence(name="PU_sequence", memory=True)

        object_next_to = ObjectAtDist(name="PU_object_next_to_agent")
        object_next_to.setup(self.agent, item_type=self.item_type, dist=1)

        object_carryable = CanCarry(name="PU_can_carry")
        object_carryable.setup(self.agent, item_type=self.item_type)

        actually_pickup = PickUp(name="PU_pickup")
        actually_pickup.setup(self.agent, item_type=item_type)

        sequence.add_children([object_next_to, object_carryable, actually_pickup])
        selector.add_children([already_carrying, sequence])

        self.bt = py_trees.trees.BehaviourTree(root=selector)

    def initialise(self):
        pass

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class PPAMoveTowards(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPAMoveTowards, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        # main PPA selector
        selector = Selector("MT_selector", memory=False)

        # postcondition
        already_next_to = ObjectAtDist("MT_already_next_to")
        already_next_to.setup(self.agent, item_type=self.item_type,
                              dist=1)  # if objects in dist = 1 -> agent is next to them :)

        # NOTE this is a workaround to be able to perform simple "move to food, pick it up, move to base and drop it"
        """already_carrying: IsCarrying
        if self.item_type == ObjectType.FOOD:
            already_carrying = IsCarrying(name="MT_already_carrying")
            already_carrying.setup(self.agent, item_type=self.item_type, quantity=1)"""

        # PPA sequence
        sequence = Sequence("MT_sequence", memory=True)

        # precondition - need to know where to move
        visited_before = IsVisitedBefore("MT_visited_before")
        visited_before.setup(agent=self.agent, item_type=self.item_type)

        see_item = ObjectAtDist("MT_see_item")
        see_item.setup(self.agent, item_type=self.item_type, dist=MAX_DISTANCE)

        # action = go to
        goto = GoTo("MT_GoTo")
        goto.setup(self.agent, item_type=self.item_type)

        sequence.add_children([visited_before, see_item, goto])
        if self.item_type == ObjectType.FOOD:
            # selector.add_children([already_carrying, already_next_to, sequence]) # NOTE workaround version from above
            selector.add_children([already_next_to, sequence])
        else:
            selector.add_children([already_next_to, sequence])

        self.bt = py_trees.trees.BehaviourTree(root=selector)

    def update(self):
        self.bt.tick()

        return self.bt.root.status

    def terminate(self, new_status):
        pass


class PPAMoveAway(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPAMoveAway, self).__init__(name)
        self.bt = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        # main PPA selector
        selector = Selector("MA_selector", memory=False)

        # postcondition
        already_away = ObjectAtDist("MA_away")
        already_away.setup(self.agent, item_type=self.item_type, dist=MAX_DISTANCE)

        already_away = Inverter(name="Inverter", child=already_away)
        already_away.setup()

        # PPA sequence
        sequence = Sequence("MA_sequence", memory=True)

        # precondition - need to know from what to move away

        visited_before = IsVisitedBefore("MA_visited_before")
        visited_before.setup(agent=self.agent, item_type=self.item_type)

        see_item = ObjectAtDist("MA_see_item")
        see_item.setup(self.agent, item_type=self.item_type, dist=self.agent.sense_radius)

        goaway = GoAway("MA_GoAway")
        goaway.setup(self.agent, item_type=self.item_type)

        sequence.add_children([visited_before, see_item, goaway])
        selector.add_children([already_away, sequence])

        self.bt = py_trees.trees.BehaviourTree(root=selector)

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class DummyNode(py_trees.behaviour.Behaviour):
    """Dummy node.

    BT node that always returns Success.
    """

    def __init__(self, name):
        """Initialize."""
        super(DummyNode, self).__init__(name)
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        """Setup."""
        self.agent = agent

    def initialise(self):
        """Pass."""
        pass

    def update(self):
        """Nothing much to do."""
        return py_trees.common.Status.SUCCESS
