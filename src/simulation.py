import logging
import random
import sys

import py_trees.trees
from PyQt5.QtWidgets import QApplication
from py_trees.composites import Sequence, Selector

from src.swarm.behaviors import *
from src.swarm.backend import TestBackend
from src.swarm.gui import SimulationWindow
from src.swarm.agent import Agent, EvoAgent, Neighbourhood
from src.swarm.objects import FoodSource, Hub
from src.swarm.types import ObjectType

NUM_OF_AGENS = 30
BOARD_SIZE = 30
GENOME = [62933, 89433, 46352, 68354, 51358, 88331, 31682, 80501, 76268, 29841, 305, 76489, 12086, 47809, 29773, 16051, 20100, 92708, 11647, 68722, 41550, 93761, 75393, 73668, 85205, 659, 98622, 85241]
#GENOME = None
DETERMINISTIC=True#False
PARAM_FILE = "AG_params.txt" #"parameters.txt"
if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    py_trees.logging.level = py_trees.logging.Level.INFO

    app = QApplication(sys.argv)

    gui = SimulationWindow(BOARD_SIZE)
    backend = TestBackend(gui, deterministic=DETERMINISTIC)
    gui.register_backend(backend)

    food = [FoodSource("jidlo"+str(random.randint(0, 100)), ObjectType.FOOD, 2) for i in range(8)]
    hub = Hub("hub", ObjectType.HUB, 4)
    backend.place_object(hub, [25, 25])

    for f in food:
        backend.place_object(f, rand=True)


    agents = list()
    for i in range(NUM_OF_AGENS):
        #if i ==0:
        #    agent = EvoAgent("agent" + str(i), sense_radius=10, init_genome=GENOME)
        #else:
        agent = EvoAgent("agent" + str(i), sense_radius=10, genome_storage_threshold=7, params_file=PARAM_FILE)
        """
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
        randomWalk = src.swarm.behaviors.RandomWalk("RandWalk")
        randomWalk.setup(agents[-1])

        move = src.swarm.behaviors.Move("MoveB")
        move.setup(agents[-1])
        root = py_trees.composites.Sequence(name="TestBehav", memory=True, children=[randomWalk, move])

        tree = py_trees.trees.BehaviourTree(root=root)
        agent.bt_wrapper = tree"""
        agents.append(agent)

        backend.register_agent(agents[-1])
        #gui.show()
    #print(type(agents[0]))


    #print("dummy")

    backend.start()

    #for agent in agents:
    #    agent.start()

    

    # r_agent = ReactiveAgentSensitive(runtime, position=[3, 3], sense_radius=2, name="ag1")
    # r_agent_sens = ReactiveAgent(runtime, position=[5, 5], sense_radius=2, name="ag2")

    # p_agent = ProactiveAgent(runtime, [5,5], sense_radius=2, name="ag3")
    # runtime.register_agent(r_agent)


    #GUI



    sys.exit(app.exec())
