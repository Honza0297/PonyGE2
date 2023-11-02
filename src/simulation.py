import logging
import random
import sys

import py_trees.trees
from PyQt5.QtWidgets import QApplication
from py_trees.composites import Sequence, Selector

from src.swarm.behaviors import *
from src.swarm.backend import TestBackend
from src.swarm.gui import SimulationWindow
import  cProfile

NUM_OF_AGENS = 300
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
    backend.setup_simulation(NUM_OF_AGENS, PARAM_FILE)

    backend.start()

    sys.exit(app.exec())
