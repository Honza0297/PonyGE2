import logging
import random
import sys

import py_trees.trees
from PyQt5.QtWidgets import QApplication
from py_trees.composites import Sequence, Selector

from src.swarm.behaviors import *
from src.swarm.backend import TestBackend
from src.swarm.gui import SimulationWindow
from src.swarm.agent import Agent, EvoAgent
from src.swarm.neighbourhood import Neighbourhood
from src.swarm.objects import FoodSource, Hub
from src.swarm.types import ObjectType
import  cProfile

NUM_OF_AGENS = 100
BOARD_SIZE = 100
GENOME = [62933, 89433, 46352, 68354, 51358, 88331, 31682, 80501, 76268, 29841, 305, 76489, 12086, 47809, 29773, 16051, 20100, 92708, 11647, 68722, 41550, 93761, 75393, 73668, 85205, 659, 98622, 85241]
# GENOME = None
DETERMINISTIC = True  # False
PARAM_FILE = "AG_params.txt"   # "AG_params.txt" "parameters.txt
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

        agent = EvoAgent("agent" + str(i), sense_radius=10, genome_storage_threshold=7, init_genome=GENOME, params_file=PARAM_FILE)

        agents.append(agent)

        backend.register_agent(agents[-1])
    backend.start()
    #cProfile.run("backend.start()", "backend_stats")

    sys.exit(app.exec())
