import logging
import sys

import py_trees.trees
from PyQt5.QtWidgets import QApplication
from py_trees.composites import Sequence, Selector

from src.swarm.behaviors import *
from src.swarm.backend import TestBackend
from src.swarm.gui import SimulationWindow
from src.swarm.agent import Agent, Neighbourhood
from src.swarm.objects import FoodSource, Hub
from src.swarm.types import ObjectType

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    py_trees.logging.level = py_trees.logging.Level.DEBUG

    app = QApplication(sys.argv)

    gui = SimulationWindow(17)
    backend_thread = TestBackend(gui)
    agents = list()
    for i in range(1):
        agent = Agent("agent" + str(i), sense_radius=6)

        selector = Selector(name="root_selector", memory=True)

        sequence = Sequence(name="subroot_sequence", memory=True)
        move_towards_food = PPAMoveTowards("move_to_food")
        move_towards_food.setup(agent, ObjectType.FOOD)

        pick_food = PPAPickuUp("pick_food")
        pick_food.setup(agent, ObjectType.FOOD)

        move_towards_base = PPAMoveTowards("move_to_base")
        move_towards_base.setup(agent, ObjectType.HUB)

        drop_food = PPADrop("drop_food_at_base")
        drop_food.setup(agent, ObjectType.FOOD)

        random_walk = CompositeRandomWalk("fallback_random_walk")
        random_walk.setup(agent)

        sequence.add_children([move_towards_food, pick_food, move_towards_base, drop_food])
        selector.add_children([sequence, random_walk])
        tree = py_trees.trees.BehaviourTree(root=selector)
        """randomWalk = src.swarm.behaviors.RandomWalk("RandWalk")
        randomWalk.setup(agents[-1])

        move = src.swarm.behaviors.Move("MoveB")
        move.setup(agents[-1])
        root = py_trees.composites.Sequence(name="TestBehav", memory=True, children=[randomWalk, move])

        tree = py_trees.trees.BehaviourTree(root=root)"""
        agent.bt = tree
        agents.append(agent)

        backend_thread.register_agent(agents[-1])
    print(type(agents[0]))

    food = FoodSource("jidlo", ObjectType.FOOD, 2)
    hub = Hub("hub", ObjectType.HUB, 2)

    backend_thread.place_object(food, [2, 2])
    backend_thread.place_object(hub, [2,11])
    print("dummy")
    backend_thread.start()
    #for agent in agents:
    #    agent.start()

    

    # r_agent = ReactiveAgentSensitive(runtime, position=[3, 3], sense_radius=2, name="ag1")
    # r_agent_sens = ReactiveAgent(runtime, position=[5, 5], sense_radius=2, name="ag2")

    # p_agent = ProactiveAgent(runtime, [5,5], sense_radius=2, name="ag3")
    # runtime.register_agent(r_agent)


    #GUI



    sys.exit(app.exec())
