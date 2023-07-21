import math
import logging
from random import random

import numpy
import numpy as np

from Direction import *
from Agent import Agent
from Runtime import Runtime


class ReactiveAgent(Agent):
    def __init__(self, runtime: Runtime, position, sense_radius=5, name="reactive_agent"):
        super().__init__(runtime, position, name)
        self.sense_radius = sense_radius
        logging.debug("New agent created: {}".format(self.name))

    def step(self):

        direction = None
        holes, corners = self.sense()
        distances = []
        if not holes:
            threshold = random()
            if threshold < 0.25:
                direction = up
            elif threshold < 0.5:
                direction = down
            elif threshold < 0.75:
                direction = left
            else:
                direction = right
        else:
            for hole in holes:
                distance = self.compute_distance(hole)
                distances.append(distance)
                min_distance_idx = distances.index(min(distances))
                closest = holes[min_distance_idx]
                direction = self.get_direction(closest)
        # if we can go in that direction

        if corners[direction] > 0:
            logging.debug("({})Moving from {} to the {}".format(self.name,self.position, direction))
            self.move(direction)

    def sense(self):
        holes = self.runtime.get_holes(position=self.position, radius=self.sense_radius)
        corners = self.runtime.get_borders(position=self.position, radius=self.sense_radius)
        return holes, corners

    def compute_distance(self, hole):
        return math.sqrt(abs(hole[0]-self.position[0])**2+abs(hole[1]-self.position[1])**2)

    def move(self, direction):
        self.runtime.move_notif(self, self.position, direction)
        self.update_pos(direction)

    def get_direction(self, closest):
        direction = None
        diff_row = abs(self.position[0]-closest[0])
        diff_col = abs(self.position[1]-closest[1])
        if diff_col > diff_row:  # move horizontally
            if self.position[1]-closest[1] > 0:  # hole is to the left
                direction = left
            else:
                direction = right
        else:
            if self.position[0]-closest[0] > 0: # hole is up
                direction = up
            else:
                direction = down
        return direction


class ReactiveAgentSensitive(ReactiveAgent):
    def __init__(self, runtime: Runtime, position, sense_radius=5, name="reactive_agent"):
        super().__init__(runtime, position, sense_radius, name)
        self.image = "reactive_agent.png"
        self.sense_radius = sense_radius
        logging.debug("New agent created: {}".format(self.name))

    def step(self):
        surr = self.sense()
        fitness = self.get_fitness_matrix(surr)
        dir = self.get_direction(fitness)
        if dir:
            self.runtime.move_notif(self,self.position, dir)
            self.update_pos(dir)

    def sense(self):
        s = self.runtime.get_surrounding(position=self.position, radius=self.sense_radius)
        r = self.sense_radius # I just don't want to write "self.sense_radius"

        # Make holes that can be removed in this turn more favorable
        if s[r+1][r] == 1:
            s[r + 1][r] *= 2
        if s[r - 1][r] == 1:
            s[r-1][r] *= 2
        if s[r][r + 1] == 1:
            s[r][r+1] *= 2
        if s[r][r - 1] == 1:
            s[r][r-1] *= 2

        return s

    def get_fitness_matrix(self, surrounding):
        fitness_matrix = np.zeros((3, 3))

        fitness_matrix[0][1] = np.sum(surrounding[0])
        fitness_matrix[1][0] = np.sum(surrounding.T[0])
        fitness_matrix[1][2] = np.sum(surrounding.T[-1])
        fitness_matrix[2][1] = np.sum(surrounding[-1])
        for i in range(self.sense_radius):
            fitness_matrix[0][1] += np.sum(surrounding[i][i:-i])
            fitness_matrix[1][0] += np.sum(surrounding.T[i][i:-i])
            fitness_matrix[1][2] += np.sum(surrounding.T[len(surrounding)-1-i][i:-i])
            fitness_matrix[2][1] += np.sum(surrounding[len(surrounding)-1-i][i:-i])

        for i in range(self.sense_radius+1):
            for j in range(self.sense_radius + 1):
                fitness_matrix[0][0] += surrounding[i][j]
                fitness_matrix[0][2] += surrounding[i][len(surrounding)-1-j]
                fitness_matrix[2][0] += surrounding[len(surrounding)-1-i][j]
                fitness_matrix[2][2] += surrounding[len(surrounding)-1-i][len(surrounding)-1-j]
        print(fitness_matrix)
        return fitness_matrix

    def get_direction(self, fitness):
        u = np.sum(fitness[0])
        d = np.sum(fitness[-1])
        l = np.sum(fitness.T[0])
        r = np.sum(fitness.T[-1])

        lst = [u, d, l, r]
        max_list = []

        if u is max(lst):
            max_list.append(up)
        elif d is max(lst):
            max_list.append(down)
        elif l is max(lst):
            max_list.append(left)
        elif r is max(lst):
            max_list.append(right)

        if max_list:
            return numpy.random.choice(max_list)
        else:
            return None