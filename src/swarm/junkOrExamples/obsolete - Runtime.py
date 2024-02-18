import logging
import random
import numpy
from .Board import QBoard, QTile
from .Direction import *
import time
import json
import http.server

agent_r = "reactive_agent.png"


class Record:
    """
    One record for data logging
    """

    def __init__(self, turn):
        self.turn = turn
        self.num_holes = 0
        self.hole_deleted = False
        self.agent_moved = False


class DataLogger:
    """
    Special logger for gathering and saving statistical data
    """
    def __init__(self):
        self.records = []
        self.current = None

    def new(self, turn):
        rec = Record(turn=turn)
        self.records.append(rec)
        self.current = self.records[-1]

    def print(self):
        print([r.__dict__ for r in self.records])

    def save_to_file(self, name):
        with open(name, "w") as logfile:
            logfile.write(json.dumps([r.__dict__ for r in self.records]))


class Runtime:
    """
    environment model - primarily provides common logic for agents: sensing, moving...
    """
    def __init__(self, board: QBoard, app, holes=[], hole_chance=1/100.):
        self.agents = []
        self.board = board
        self.holes = holes
        self.dimension = self.board.dimension
        if holes:
            for hole in holes:
                self.board.tiles[hole[0]][hole[1]].create_hole()
        self.steps = 0
        self.hole_chance = hole_chance  # percent
        self.headless = False  # TODO
        self.dl = DataLogger()

        self.app = app
        self.server = None # TODO



        logging.debug("==========================")
        logging.debug("Setting up the simulation")
        logging.debug(
            f"""Board_size: {self.board.dimension}
           Hole_chance: {self.hole_chance}
           Headless: {self.headless}
        """)
        logging.debug("==========================")



    def step(self):
        """
        One step of the simulation
        """
        self.dl.new(self.steps)
        logging.debug("----------")
        logging.debug(f"Step: {self.steps}")
        logging.debug(f"Holes: {self.holes}")
        self.generate_holes()
        self.dl.current.num_holes = len(self.holes)
        for agent in self.agents:
            agent.step()
        self.steps += 1

    def register_agent(self, agent):
        self.agents.append(agent)
        self.board.tiles[agent.position[0]][agent.position[1]].image = agent.image

    def generate_holes(self):
        for row in self.board.tiles:
            for square in row:  # square: QSquare
                if square.position in self.get_agent_positions() or square.position in self.holes:
                    continue
                threshold = random.random()
                if self.hole_chance > threshold:
                    self.holes.append(square.position)
                    square.create_hole()

    def get_agent_positions(self):
        ret = list()
        for agent in self.agents:
            ret.append(tuple(agent.position))
        return ret

    def get_surrounding(self, position, radius):
        dim = 2 * radius + 1
        offset = (position[0] - radius, position[1] - radius)
        surrounding = numpy.zeros((dim, dim))
        for row in range(position[0] - radius, position[0] + radius + 1):
            for col in range(position[1] - radius, position[1] + radius + 1):
                if (row, col) in self.holes:
                    surrounding[row - offset[0]][col - offset[1]] = 1
        for i_r in range(len(surrounding[0])):
            for i_c in range(len(surrounding)):
                if self.is_out_of_board(i_r + offset[0], i_c + offset[1]):
                    surrounding[i_r][i_c] = -0.1
                # if tuple((i_r, i_c)) in self.get_agent_positions():
                #    surrounding[i_r][i_c] = -1
        return surrounding

    def get_holes(self, position, radius):
        pos_holes = []
        for row in range(position[0] - radius, position[0] + radius + 1):
            for col in range(position[1] - radius, position[1] + radius + 1):
                if (row, col) in self.holes:
                    pos_holes.append((row, col))
        return pos_holes

    def get_borders(self, position, radius):
        ret = {up: float("inf"), down: float("inf"), left: float("inf"), right: float("inf")}
        dim = len(self.board.tiles[0])
        ret_up_candidate = dim - 1 - position[0]

        ret[down] = ret_up_candidate if ret_up_candidate <= radius else ret[down]
        ret[up] = position[0] if position[0] <= radius else ret[up]

        ret_right_candidate = dim - 1 - position[1]
        ret[right] = ret_right_candidate if ret_right_candidate <= radius else ret[right]
        ret[left] = position[1] if position[1] <= radius else ret[left]
        return ret

    def move_notif(self, agent, curr, direction):
        self.dl.current.agent_moved = True
        if agent not in self.agents:
            return

        self.board.tiles[curr[0]][curr[1]].image = None
        self.board.tiles[curr[0]][curr[1]].update()
        new_pos = [curr[0], curr[1]]

        if direction == up:
            self.board.tiles[curr[0] - 1][curr[1]].set_image(agent_r)
            self.board.tiles[curr[0] - 1][curr[1]].update()
            new_pos[0] -= 1
        elif direction == down:
            self.board.tiles[curr[0] + 1][curr[1]].set_image(agent_r)
            self.board.tiles[curr[0] + 1][curr[1]].update()
            new_pos[0] += 1
        elif direction == left:
            self.board.tiles[curr[0]][curr[1] - 1].set_image(agent_r)
            self.board.tiles[curr[0]][curr[1] - 1].update()
            new_pos[1] -= 1
        elif direction == right:
            self.board.tiles[curr[0]][curr[1] + 1].set_image(agent_r)
            self.board.tiles[curr[0]][curr[1] + 1].update()
            new_pos[1] += 1

        logging.debug(f"(runtime) Agent has notified about move from {curr} to the {direction}.")

        if tuple(new_pos) in self.holes:
            self.dl.current.hole_deleted = True
            self.holes.remove(tuple(new_pos))

    def is_out_of_board(self, i_r, i_c):
        if i_r < 0 or i_c < 0 or \
                i_r > self.dimension - 1 or i_c > self.dimension - 1:
            return True
        else:
            return False
