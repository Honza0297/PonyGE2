import py_trees
from py_trees.composites import Sequence, Selector
import random
from src.swarm.math import *
from src.swarm.models import TileModel
from src.swarm.types import ObjectType, Direction
from py_trees.decorators import Inverter


# TODO
# 1) Check jestli isvisited before je na typ objektu nebo na konkrétní instance
  # * plus aadesh to má na vzdálenost, ne vyloženě být vedle - mám to taky tak?
# 2) objectatdist by neměl setovat goalobject, ale jen množiny daných objektů
 #    !!! Pro aadese je objectatdist/neighbourobjects něco jako "pochop, co vidíš"! Projde totiž všechny políčka v dohledu a utřídí si je podle typu
class IsVisitedBefore(py_trees.behaviour.Behaviour):
    """
    Checks if agent's memory contains given object type (not particular object)
    """
    def __init__(self, name):
        super(IsVisitedBefore, self).__init__(name)
        self.agent = None
        self.item_type = None

    def setup(self, agent, item=None, item_type=None) -> None:
        self.agent = agent
        self.item_type = item_type if item_type else item

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        if self.agent.place_types_visited[self.item_type]:
            status = py_trees.common.Status.SUCCESS

        return status

    def terminate(self, new_status):
        pass


class ObjectAtDist(py_trees.behaviour.Behaviour):
    """
    Checks if there are objects of the given type in the given distance.
    If dist = 1, then the agent is able to pick up the near object.
    """

    def __init__(self, name):
        super(ObjectAtDist, self).__init__(name)
        self.distance = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None, dist=1) -> None:
        self.agent = agent
        if isinstance(item_type, str):
            self.item_type = ObjectType.str2enum(item_type)
        else:
            self.item_type = item_type
        self.distance = dist

    def initialise(self) -> None:
        pass

    def update(self) -> py_trees.common.Status:
        status = py_trees.common.Status.FAILURE
        if not self.agent.neighbourhood.valid:
            self.logger.debug("running, neighbourhood not valid -> waiting to the next iteration")
            return py_trees.common.Status.RUNNING

        tiles_with_object = list()
        # if not self.agent.neighbourhood.valid:
        #    status = py_trees.common.Status.INVALID
        if tuple(self.agent.position) == (5,0):
            pass
        if not self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][self.agent.neighbourhood.center[1]]:
            pass  # NOTE Sometimes, center is None, could not reproduce in approx. 3k runs though...
        if self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][self.agent.neighbourhood.center[1]].position != tuple(self.agent.position):
            raise RuntimeError("Center position in neighbourhood {} differs from agent position {}".format(
                self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][
                    self.agent.neighbourhood.center[1]].position, self.agent.position))

        """for row in self.agent.neighbourhood.neighbourhood:
            # TODO optimize: skip rows too far
            for tile in row:
                if tile and compute_distance(tile.position, self.agent.position) <= self.distance \
                        and tile.type == self.item_type:
                    tiles_with_object.append(tile)
                    self.logger.debug("DEBUG: found tile of type {} in dist {}".format(tile.type.value, self.distance))"""
        objects = self.agent.neighbourhood.get_objects(object_type=self.item_type, max_distance=self.distance)
        if objects:
            status = py_trees.common.Status.SUCCESS
            self.logger.debug("SUCCESS, there {} object{} of type {} in distance={}".format(
                "are" if len(objects) > 1 else "is", "s" if len(objects) > 1 else "",
                self.item_type.value, self.distance))
            # TODO chci to někam uložit?
        else:
            self.logger.debug("FAILURE, no object of type {} in distance={}".format(self.item_type.value,
                                                                                    self.distance))
            self.logger.debug("\n{}".format(self.agent.neighbourhood))
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

    def setup(self, agent, item=None, item_type=None, change_prob=25):
        self.agent = agent
        self.change_prob = change_prob  # percent

    def initialise(self):
        pass

    def update(self):
        change_direction = random.randint(1, 100)
        if change_direction <= self.change_prob:  # with prob = self.change_prob %, change direction of random walk
            self.agent.heading = random.choice((Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT))

        # set goal as the farthest tile in direct sight (not occupied) in the desired direction
        goal = None
        curr_pos = self.agent.neighbourhood.center
        tmp_tile = self.agent.neighbourhood.get_next_tile_in_dir(curr_pos, self.agent.heading)
        while tmp_tile and not tmp_tile.occupied:
            goal = tmp_tile  # temp_goal is current tile
            curr_pos = self.agent.neighbourhood.get_relative_pos(goal.position)  # change pos (helping var) to the goal pos
            tmp_tile = self.agent.neighbourhood.get_next_tile_in_dir(curr_pos, Direction.UP)

        if goal:  # goal found (i.e. the path is clear)
            self.agent.goal = goal
            #self.blackboard.set(name="goalObject", value=goal, overwrite=True)
            status = py_trees.common.Status.SUCCESS
        else:  # cannot go in desired direction
            self.agent.heading = random.choice((Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT))
            status = py_trees.common.Status.FAILURE

        return status

    def terminate(self, new_status):
        pass


def remove_invalid_headings(agent):
    heading = []
    if not isinstance(agent.heading, (tuple, list)):
        agent.heading = [agent.heading]
    for direction in agent.heading:
        candidate_pos = pos_from_heading(agent.position, direction)
        # Dimension check
        if candidate_pos[0] < 0 or candidate_pos[1] < 0 or candidate_pos[0] >= agent.backend.board_model.dimension or candidate_pos[1] >= agent.backend.board_model.dimension:
            continue
        # occupancy check
        elif agent.neighbourhood.get_next_tile_in_dir(agent.neighbourhood.center, direction).occupied:
            continue
        else:
            heading.append(direction)

    return heading


class SetNextStep(py_trees.behaviour.Behaviour):
    """
    Computes next position based on current goal
    """
    def __init__(self, name):
        super(SetNextStep, self).__init__(name)
        self.towards = None
        self.blackboard = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None, towards=True):
        self.agent = agent
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
       # # self.blackboard.register_key(key="nearObjects", access=py_trees.common.Access.WRITE)  # todo better name for key
        #self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.WRITE)
        self.towards = towards

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE
        self.agent.next_step = self.agent.position

        """if self.blackboard.exists(name="goalObject"):
            goal = self.blackboard.get(name="goalObject")
            self.agent.heading = compute_heading(self.agent.position, goal.position, towards=self.towards)
        else:
            raise ValueError("No valid goalObject present")"""
        if self.agent.goal:
            goal = self.agent.goal
            self.agent.heading = compute_heading(self.agent.position, goal.position, towards=self.towards)
        else:
            raise ValueError("No goal present")

        if isinstance(self.agent.heading, list):  # broad heading
            current_distance = compute_distance(self.agent.position, goal.position)
            self.agent.heading = remove_invalid_headings(self.agent)
            if self.agent.heading:
                # todo not random, but based on quality - current distance change
                self.agent.heading = random.choice(self.agent.heading)
                self.agent.next_step = pos_from_heading(self.agent.position, self.agent.heading)
                status = py_trees.common.Status.SUCCESS
        else:
            # If direct heading not possible (obstacle), use broad heading
            if not remove_invalid_headings(self.agent):
                self.agent.heading = Direction.broad_direction(self.agent.heading)
            self.agent.heading = remove_invalid_headings(self.agent)
            if self.agent.heading:
                # todo not random, but based on quality - current distance change
                self.agent.heading = random.choice(self.agent.heading)
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
        #self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        #self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.READ)

    def initialise(self):
        pass

    def update(self):
        if not self.agent.next_step:
            status = py_trees.common.Status.FAILURE
        elif tuple(self.agent.position) == tuple(self.agent.next_step):
            self.logger.debug(
                "SUCCESS, {} is already at next step {}".format(self.agent.name, self.agent.next_step))
            #self.blackboard.unset(key="goalObject")  # unset goal because cannot move towards it. if error check for existence
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
                # todo
                status = py_trees.common.Status.SUCCESS
            else:
                self.logger.debug(
                    "FAILURE, resp.position = {} and agent's next step = {} not the same".format(resp.position,
                                                                                                 self.agent.next_step))
                #self.blackboard.unset(key="goalObject")  # unset goal because cannot move towards it. if error check for existence
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

    def setup(self, agent, item=None, item_type=None, quantity=1):
        self.agent = agent
        self.item_type = item_type
        self.quantity = quantity

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        for item in self.agent.inventory:
            if item.type == self.item_type:
                self.logger.debug("SUCCESS, item of type {} found in inventory".format(self.item_type))
                status = py_trees.common.Status.SUCCESS
                break
        if self.agent.dropping_item == self.item_type:  # when in the middle of dropping
            self.logger.debug("SUCCESS, item of type {} is the item to be dropped".format(self.item_type))
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
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.READ)
        self.item_type = None

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.SUCCESS  # TODO change once items can be non carryable
        item: TileModel
        if self.blackboard.exists(name="goalObject"):
            # item = self.blackboard.get(name="goalObject")
            # TODO when items start to be carryable and non carryable, implement here. :-)

            status = py_trees.common.Status.SUCCESS
        self.logger.debug("SUCCESS, everything is carryable :)")
        return status

    def terminate(self, new_status):
        pass


class IsDroppable(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(IsDroppable, self).__init__(name)
        self.item_type = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        pass

    def update(self):
        # TODO once items start to be non-droppable, implement here
        self.logger.debug("SUCCESS, everything is droppable :)")
        return py_trees.common.Status.SUCCESS

    def terminate(self, new_status):
        pass


class PickUp(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PickUp, self).__init__(name)
        #self.blackboard = None
        self.running = None
        self.agent = None

    def setup(self, agent, item=None, item_type=None):
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
                    self.logger.debug("SUCCESS, {} picked up an object".format(self.agent.name))
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

    def setup(self, agent, item=None, item_type=None):
        self.agent = agent
        self.item_type = item_type
        self.running = False

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
            if tile and (not tile.occupied or tile.object.type == ObjectType.HUB):
                self.logger.debug("SUCCESS, can drop somewhere")
                status = py_trees.common.Status.SUCCESS
        if status == py_trees.common.Status.FAILURE:
            self.logger.debug("FAILURE, cannot drop item")
        return status

    def terminate(self, new_status):
        pass


###
# Composite non PPA behaviors
###
class PPARandomWalk(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPARandomWalk, self).__init__(name)
        self.bt = None

    def setup(self, agent, item=None, item_type=None):
        rw = RandomWalk(name="CRW_random_walk")
        rw.setup(agent, item, item_type)

        sns = SetNextStep(name="CRW_next_step")
        sns.setup(agent)

        move = Move(name="CRW_move")
        move.setup(agent)

        sequence = Sequence(name="CRW_sequence", memory=True)
        sequence.add_children([rw, sns, move])

        self.bt = py_trees.trees.BehaviourTree(root=sequence)

    def initialise(self):
        pass

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


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
        set_next_step = SetNextStep("GT_setnextstep")
        set_next_step.setup(self.agent, item_type=self.item_type)
        move = Move("GT_move")
        move.setup(self.agent)

        # If we planned move and failed, we should consider setting new plan -> memory = False
        sequence = Sequence("GT_sequence", memory=False)
        sequence.add_children([set_next_step, move])
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
        set_next_step = SetNextStep("GA_setnextstep")
        set_next_step.setup(self.agent, item_type=self.item_type, towards=False)
        move = Move("GA_move")
        move.setup(self.agent)

        # If we planned move and failed, we should consider setting new plan -> memory = False
        sequence = Sequence("GA_sequence", memory=False)
        sequence.add_children([set_next_step, move])
        self.bt = py_trees.trees.BehaviourTree(root=sequence)

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


###
# PPA BEHAVIORS
###


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
        is_dropped = Inverter(name="DRP_is_dropped", child=already_carrying)

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
        object_next_to.setup(self.agent, item_type=self.item_type)

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

        # TODO this is a workaround to be able to perform simple "move to food, pick it up, move to base and drop it"
        """already_carrying: IsCarrying
        if self.item_type == ObjectType.FOOD:
            already_carrying = IsCarrying(name="MT_already_carrying")
            already_carrying.setup(self.agent, item_type=self.item_type, quantity=1)"""

        # PPA sequence
        sequence = Sequence("MT_sequence", memory=True)

        # precondition - need to know where to move
        see_item = ObjectAtDist("MT_see_item")
        see_item.setup(self.agent, item_type=self.item_type, dist=self.agent.sense_radius)

        # action = go to
        goto = GoTo("MT_GoTo")
        goto.setup(self.agent, item_type=self.item_type)

        sequence.add_children([see_item, goto])
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
        already_away.setup(self.agent, item_type=self.item_type, dist=self.agent.sense_radius)

        already_away = Inverter(name="Inverter", child=already_away)
        already_away.setup()

        # PPA sequence
        sequence = Sequence("MA_sequence", memory=True)

        # precondition - need to know from what to move away
        see_item = ObjectAtDist("MA_see_item")
        see_item.setup(self.agent, item_type=self.item_type, dist=self.agent.sense_radius)

        goaway = GoAway("MA_GoAway")
        goaway.setup(self.agent, item_type=self.item_type)

        sequence.add_children([see_item, goaway])
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
