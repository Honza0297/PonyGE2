"""This is the mapper class which maps the xml file."""


from typing import Type
import xml.etree.ElementTree as ET
import py_trees
from py_trees.composites import Sequence, Selector  # noqa: F401
import pydot

"""
Thisi is commented by now as I have no behaviors
from swarms.behaviors.scbehaviors import (      # noqa: F401
    MoveTowards, MoveAway, Explore, CompositeSingleCarry,
    CompositeDrop, CompositeDropPheromone, CompositeSensePheromone,
    CompositeSendSignal, CompositeReceiveSignal,
    MoveAwayNormal, MoveTowardsNormal, ExploreNormal
    )
from swarms.behaviors.sbehaviors import (       # noqa: F401
    IsCarrying, NeighbourObjects, Move, IsDropable,
    IsVisitedBefore, IsInPartialAttached, CanMove,
    DidAvoidedObj, IsCarryable, IsAgentDead, IsAttractivePheromone,
    IsRepulsivePheromone, IsSignalActive, SignalDoesNotExists,
    PheromoneExists, DummyNode
    )
"""
import swarm.types as types
from swarm.behaviors import ( # noqa 401
    IsVisitedBefore,
    ObjectAtDist as NeighbourObjects,
    IsCarrying,
    CanCarry,
    IsDroppable,
    CanDrop,
    PPARandomWalk,
    PPADrop,
    PPAPickUp,
    PPAMoveTowards,
    PPAMoveAway,
    DummyNode
)

from py_trees.decorators import SuccessIsRunning, Inverter


class BTConstruct:
    """Mapper to map from xml to BT.

    This class maps xml file generated from grammar to
    Behavior Trees
    """

    def __init__(self, filename, agent, xmlstring=None):
        """Initialize the attributes for mapper.

        Args:
            filename: name of xml file that is to be mapped into BT
            agent: agent object
            xmlstring: xml stream instead of file
        """
        self.filename = filename
        self.xmlstring = xmlstring
        self.agent = agent

    def xmlfy(self):
        """Convert [] to <>."""
        self.xmlstring = self.xmlstring.replace('[', '<')
        self.xmlstring = self.xmlstring.replace(']', '>')
        self.xmlstring = self.xmlstring.replace('%', '"')

    def create_bt(self, root):
        """Recursive method to construct BT."""
        #print('root',root, len(root))
        def leafnode(root):
            node_text = root.text
            # If the behavior needs to look for specific item
            if node_text.find('_') != -1:
                nodeval = node_text.split('_')
                # Check for behavior inversion
                if len(nodeval) == 2:
                    method, item = nodeval
                    behavior = eval(method)(method + str(
                        self.agent.backend.random.randint(
                            100, 200)) + '_' + item + '_' + root.tag)
                    item = types.ObjectType.str2enum(item)
                    behavior.setup(agent=self.agent, item_type=item)
                else:
                    method, item, _ = nodeval
                    behavior = eval(method)(
                        method + str(
                            self.agent.backend.random.randint(
                                100, 200)) + '_' + item + '_inv' + '_' + root.tag)
                    item = types.ObjectType.str2enum(item)
                    behavior.setup(agent=self.agent, item_type=item)
                    behavior = Inverter(name="Inverter", child=behavior)
                    behavior.setup()
                if type(item) is str:
                    item = types.ObjectType.str2enum(item)

            else:
                method = node_text
                behavior = eval(method)(method + str(
                    self.agent.backend.random.randint(100, 200)))
                behavior.setup(agent=self.agent)
            return behavior

        if len(list(root)) == 0:
            return leafnode(root)
        else:
            list1 = []
            for node in list(root):
                if node.tag in ['Selector', 'Sequence']:
                    composits = eval(node.tag)(node.tag + str(
                        self.agent.backend.random.randint(10, 90)), memory=True if node.tag == "Sequence" else False)
                    # print('composits', composits, node)
                list1.append(self.create_bt(node))
                try:
                    if composits:
                        nodepop = list1.pop()
                        try:
                            composits.add_children(nodepop)
                        except TypeError:
                            composits.add_children([nodepop])
                        if composits not in list1:
                            list1.append(composits)
                except (AttributeError, IndexError, UnboundLocalError) as e:
                    pass
            return list1

    def bt_from_xml(self):
        """Create a tree from xml."""
        if self.xmlstring is not None:
            self.xmlfy()
            tree = ET.fromstring(self.xmlstring)
            self.root = tree

        elif self.filename is not None:
            tree = ET.parse(self.filename)
            self.root = tree.getroot()
        else:
            print("Cannot create BT. Check the filename or stream")
            exit()
        # print('root tree', self.root)
        whole_list = self.create_bt(self.root)
        top = eval(self.root.tag)('Root' + self.root.tag,memory=True if self.root.tag == "Sequence" else False)
        # print('whole list', whole_list)
        # print(dir(top))
        top.add_children(whole_list)
        self.behaviour_tree = py_trees.trees.BehaviourTree(top)
        # py_trees.logging.level = py_trees.logging.Level.DEBUG
        # py_trees.display.print_ascii_tree(top)

    def visualize(self, name='bt.png', mode="d"):
        """Save bt graph to a file."""
        if mode == "d": # display
            print(py_trees.display.ascii_tree(self.behaviour_tree.root))
        else:
            py_trees.display.render_dot_tree(self.behaviour_tree.root, name=name)