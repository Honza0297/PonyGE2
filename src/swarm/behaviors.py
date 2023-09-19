import py_trees
from py_trees.composites import Sequence, Selector
import random
from src.swarm.math import *
#import src.swarm.packets
from src.swarm.models import TileModel
from src.swarm.types import ObjectType
#from src.swarm.agent import Agent
from py_trees.decorators import Inverter


# TODO: keys na blackboardu dat jako typy do types.py
# TODO: make agent memoryful - classes Memorize/Forget/Remember
class ObjectAtDist(py_trees.behaviour.Behaviour):
    """
    Checks if there are objects of the given type in the given distance.
    Result in BT blackboard nearObjects key
    If dist = 1, then the agent is able to pick up the near object.
    """

    def __init__(self, name):
        super(ObjectAtDist, self).__init__(name)

    def setup(self, agent, obj_type, dist=1) -> None:
        self.agent = agent

        if type(obj_type) is str:
            self.obj_type = ObjectType.str2enum(obj_type)
        else:
            self.obj_type = obj_type

        self.distance = dist
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="nearObjects", access=py_trees.common.Access.WRITE)  # todo better name for key

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
        if self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][
            self.agent.neighbourhood.center[1]].position != tuple(self.agent.position):
            raise RuntimeError("Center position in neighbourhood {} differs from agent position {}".format(
                self.agent.neighbourhood.neighbourhood[self.agent.neighbourhood.center[0]][
                    self.agent.neighbourhood.center[1]].position, self.agent.position))

        for row in self.agent.neighbourhood.neighbourhood:
            # TODO optimize: skip rows too far
            for tile in row:
                if tile and compute_distance(tile.position, self.agent.position) <= self.distance \
                        and tile.type == self.obj_type:
                    tiles_with_object.append(tile)
                    self.logger.debug("DEBUG: found tile of type {} in dist {}".format(tile.type.value, self.distance))

        if tiles_with_object:
            status = py_trees.common.Status.SUCCESS
            self.blackboard.set("nearObjects", tiles_with_object, overwrite=True)
            self.logger.debug("SUCCESS, there {} object{} of type {} in distance={}".format(
                "are" if len(tiles_with_object) > 1 else "is", "s" if len(tiles_with_object) > 1 else "",
                self.obj_type.value, self.distance))
        else:
            self.logger.debug("FAILURE, no object of type {} in distance={}".format(self.obj_type.value,
                                                                                      self.distance))
            self.logger.debug("\n{}".format(self.agent.neighbourhood))
        return status
        # copying values out from Neighbourhood() to shorten expressions


    def terminate(self, new_state):
        pass


class RandomWalk(py_trees.behaviour.Behaviour):
    """
    Prepare the intention to move in a random direction.
    Direction is updated with prob = self.change_prob
    """

    def __init__(self, name):
        super(RandomWalk, self).__init__(name)

    def setup(self, agent):
        self.agent = agent
        self.axis = 0
        self.delta = 0
        self.change_prob = 25  # percent
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.WRITE)

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        change_direction = random.randint(1, 100)
        if change_direction <= self.change_prob:  # with prob = 10 %, change direction of random walk
            self.axis = random.randint(0, 1)
            self.delta = random.randint(0, 1) * 2 - 1
            # self.logger.debug("BT: Axis and delta changed to {}, {}".format(self.axis, self.delta))

        new_pos = list(self.agent.position)
        new_pos[self.axis] += self.delta
        new_pos_in_neighbourhood = [self.agent.sense_radius, self.agent.sense_radius]
        new_pos_in_neighbourhood[self.axis] += self.delta
        # self.logger.debug("BT: New position should be {}".format(new_pos))

        if self.agent.neighbourhood.neighbourhood[new_pos_in_neighbourhood[0]][new_pos_in_neighbourhood[1]] \
                and not self.agent.neighbourhood.neighbourhood[new_pos_in_neighbourhood[0]][
            new_pos_in_neighbourhood[1]].occupied:
            self.agent.next_step = new_pos
            self.logger.debug("SUCCESS, try_to_move from {} to {}".format(self.agent.position, self.agent.next_step))
            next_tile = self.agent.neighbourhood.neighbourhood[new_pos_in_neighbourhood[0]][new_pos_in_neighbourhood[1]]
            self.blackboard.set(name="goalObject", value=next_tile, overwrite=True)
            status = py_trees.common.Status.SUCCESS
        else:  # cannot move for some reason
            self.axis = random.randint(0, 1)
            self.delta = random.randint(0, 1) * 2 - 1
            self.logger.debug("FAILURE, cannot move")
            status = py_trees.common.Status.FAILURE

        return status

    def terminate(self, new_status):
        pass


class SetNextStep(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(SetNextStep, self).__init__(name)

    def setup(self, agent, item_type):
        self.agent = agent
        self.item_type = item_type
        self.nearest_object = None
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="nearObjects", access=py_trees.common.Access.READ)  # todo better name for key
        self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.WRITE)

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        # self.item is just object type -> wee need to check blackboard

        items = self.blackboard.get("nearObjects")
        if not items or items[0].type != self.item_type:
            self.logger.debug("FAILURE, objects in nearObjects are of type {} instead of {}".format(
                "NoObject" if not items else items[0].type.value, self.item_type.value))
            status = py_trees.common.Status.FAILURE
        else:

            # choose the nearest object if not already chosen (and still present in blackboard)
            newly_chosen = False
            if not (self.nearest_object and self.nearest_object in items):
                newly_chosen = True
                nearest_objects = list()
                nearest_dist = self.agent.sense_radius
                for obj in items:
                    if compute_distance(self.agent.position, obj.position) == nearest_dist:
                        nearest_objects.append(obj)
                    elif compute_distance(self.agent.position, obj.position) < nearest_dist:
                        nearest_objects = [obj]
                        nearest_dist = compute_distance(self.agent.position, obj.position)
                # choose randomly if there are more objects in the same distance
                self.nearest_object = random.choice(nearest_objects)
                # self.logger.debug("DEBUG, nearest object of type {} is at {}".format(self.item_type, self.nearest_object.position))
                self.blackboard.set(name="goalObject", value=self.nearest_object, overwrite=True)
            # get where to move and set it
            axis, delta = choose_direction(self.agent.position, self.nearest_object.position)
            next_step = list(self.agent.position)
            next_step[axis] += delta
            self.logger.debug("next_step should be {}".format(next_step))
            self.agent.next_step = next_step
            self.logger.debug("SUCCESS, nearest object {} changed, current is {} at position{}".format(
                "" if newly_chosen else "not", self.nearest_object.type, self.nearest_object.position))
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

    def setup(self, agent):
        self.agent = agent
        self.running = False
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.READ)


    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE

        if tuple(self.agent.position) == tuple(self.agent.next_step):
            self.logger.debug(
                "SUCCESS, {} is already at next step {}".format(self.agent.name, self.agent.next_step))
            status = py_trees.common.Status.SUCCESS
        else:
            #self.agent.request_queue.put(src.swarm.packets.Move(self.agent.name, self.agent.next_step))
            resp = self.agent.backend.move_agent(self.agent, self.agent.position, self.agent.next_step)
            if resp and list(resp.position) == list(self.agent.next_step):
                # self.agent.position = resp.position
                self.logger.debug(
                    "SUCCESS, {} got response corresponding to its next_step={}".format(self.agent.name,
                                                                                        self.agent.next_step))
                self.agent.set_position(resp.position)
                self.agent.neighbourhood.valid = False  # we have moved -> neighbourhood is invalid
                # todo

                goal = self.blackboard.get(name="goalObject")
                if compute_distance(goal.position, self.agent.position) <= 1:
                    status = py_trees.common.Status.SUCCESS
                else:
                    status = py_trees.common.Status.RUNNING

            else:
                self.logger.debug(
                    "FAILURE, resp.position = {} and agent's next step = {} not the same".format(resp.position,
                                                                                        self.agent.next_step))
        return status

    def terminate(self, new_status):
        pass


class IsCarrying(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(IsCarrying, self).__init__(name)
        self.quantity = None
        self.item_type = None
        self.agent = None

    def setup(self, agent, item_type, quantity=1):
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

    def setup(self, agent, item):
        self.agent = agent
        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.READ)

    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.SUCCESS  # TODO change once items can be non carryable
        item: TileModel
        if self.blackboard.exists(name="goalObject"):
            item = self.blackboard.get(name="goalObject")
            # TODO when items start to be carryable and non carryable, implement here. :-)

            status = py_trees.common.Status.SUCCESS
        self.logger.debug("SUCCESS, everything is carryable :)")
        return status

    def terminate(self, new_status):
        pass


class IsDroppable(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(IsDroppable, self).__init__(name)

    def setup(self, agent, item_type):
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

    def setup(self, agent, item_type):
        self.running = False
        self.agent = agent

        item = None

        num, cells = self.agent.neighbourhood.get(item_type)
        if num > 0:
            item = random.choice(cells)

        self.blackboard = py_trees.blackboard.Client(name=self.agent.name, namespace=self.agent.name)
        if item:
            self.blackboard.register_key(key="goalObject", access=py_trees.common.Access.WRITE)

            self.blackboard.set("goalObject", item)
    def initialise(self):
        pass

    def update(self):
        status = py_trees.common.Status.FAILURE
        if self.blackboard.exists(name="goalObject"):
            item = self.blackboard.get(name="goalObject")  # item = TileModel
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

    def setup(self, agent, item_type):
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

    def check_drop_status(self):
        status = py_trees.common.Status.FAILURE


        return status

    def terminate(self, new_status):
        pass


class CanDrop(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(CanDrop, self).__init__(name)

    def setup(self, agent, item_type):
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
            if tile and (not tile.occupied or tile.obj_type == ObjectType.HUB):
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
class CompositeRandomWalk(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(CompositeRandomWalk, self).__init__(name)

    def setup(self, agent):
        rw = RandomWalk(name="CRW_random_walk")
        rw.setup(agent)

        move = Move(name="CRW_move")
        move.setup(agent)

        sequence = Sequence(name="CRW_sequence", memory=True)
        sequence.add_children([rw, move])

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

    def setup(self, agent, item_type):
        self.agent = agent
        self.item_type = item_type

    def initialise(self):
        set_next_step = SetNextStep("GT_setnextstep")
        set_next_step.setup(self.agent, self.item_type)
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


###
# PPA BEHAVIORS
###


class PPADrop(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPADrop, self).__init__(name)

    def setup(self, agent, item_type):
        self.agent = agent
        self.item_type = item_type

        selector = Selector(name="DRP_selector", memory=True)
        # postcondition
        already_carrying = IsCarrying(name="DRP_already_carrying")
        already_carrying.setup(self.agent, item_type=self.item_type,
                               quantity=1)
        is_dropped = Inverter(name="DRP_isdropped", child=already_carrying)

        sequence = Sequence(name="DRP_sequence", memory=True)

        is_dropable = IsDroppable(name="DRP_isdroppable")
        is_dropable.setup(agent, item_type)

        can_drop = CanDrop(name="DRP_canDrop")
        can_drop.setup(agent, item_type)

        actually_drop = Drop(name="DRP_actually_drop")
        actually_drop.setup(agent, item_type)

        sequence.add_children([is_dropable, actually_drop])
        selector.add_children([is_dropped, sequence])

        self.bt = py_trees.trees.BehaviourTree(root=selector)

    def initialise(self):
        pass

    def update(self):
        self.bt.tick()
        return self.bt.root.status

    def terminate(self, new_status):
        pass


class PPAPickuUp(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PPAPickuUp, self).__init__(name)

    def setup(self, agent, item_type):
        self.agent = agent
        self.item_type = item_type

        selector = Selector(name="PU_selector", memory=True)
        # postcondition
        already_carrying = IsCarrying(name="PU_already_carrying")
        already_carrying.setup(self.agent, item_type=self.item_type, quantity=1)

        sequence = Sequence(name="PU_sequence", memory=True)

        object_next_to = ObjectAtDist(name="PU_obje_next_to_agent")
        object_next_to.setup(self.agent, self.item_type)

        object_carryable = CanCarry(name="PU_cancarry")
        object_carryable.setup(self.agent, self.item_type)

        actually_pickup = PickUp(name="PU_pickup")
        actually_pickup.setup(self.agent)

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

    def setup(self, agent, item_type):
        self.agent = agent
        self.item_type = item_type
        pass

    def initialise(self):
        # main PPA selector
        selector = Selector("MT_selector", memory=False)

        # postcondition
        already_next_to = ObjectAtDist("MT_already_next_to")
        already_next_to.setup(self.agent, self.item_type, dist=1)  # if objects in dist = 1 -> agent is next to them :)

        # TODO this is a workaround to be able to perform simple "move to food, pick it up, move to base and drop it"
        already_carrying: IsCarrying
        if self.item_type == ObjectType.FOOD:
            already_carrying = IsCarrying(name="MT_already_carrying")
            already_carrying.setup(self.agent, item_type=self.item_type, quantity=1)

        # PPA sequence
        sequence = Sequence("MT_sequence", memory=True)

        # precondition - need to know where to move
        see_item = ObjectAtDist("MT_see_item")
        see_item.setup(self.agent, self.item_type, dist=self.agent.sense_radius)

        # action = go to
        goto = GoTo("MT_GoTo")
        goto.setup(self.agent, self.item_type)

        sequence.add_children([see_item, goto])
        if self.item_type == ObjectType.FOOD:
            selector.add_children([already_carrying, already_next_to, sequence])
        else:
            selector.add_children([already_next_to, sequence])

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

    def setup(self, agent, item=None):
        """Setup."""
        self.agent = agent
        self.item = item

    def initialise(self):
        """Pass."""
        pass

    def update(self):
        """Nothing much to do."""
        return py_trees.common.Status.SUCCESS