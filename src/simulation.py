#! /usr/bin/python

import logging
import random
import sys

import py_trees.trees
from PyQt5.QtWidgets import QApplication
from py_trees.composites import Sequence, Selector

from swarm.backend import TestBackend
from swarm.gui import SimulationWindow
import  cProfile

NUM_OF_AGENS = 100
BOARD_SIZE = 100
DETERMINISTIC = True  # False
PARAM_FILE = "AG_params.txt"   # "AG_params.txt" "parameters.txt
if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    py_trees.logging.level = py_trees.logging.Level.INFO

    app = QApplication(sys.argv)

    gui = SimulationWindow(BOARD_SIZE)
    backend = TestBackend(gui, deterministic=DETERMINISTIC)
    backend.setup_simulation(NUM_OF_AGENS, PARAM_FILE)
    gui.register_backend(backend)

    backend.start()

    sys.exit(app.exec())
