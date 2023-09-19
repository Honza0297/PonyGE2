import logging
import random
import sys
import time

import py_trees.trees
from PyQt5 import QtCore

from src.swarm import types
from src.swarm.types import ObjectType
from src.swarm.packets import *
import src.algorithm.parameters
from src.operators.initialisation import initialisation
from src.fitness.evaluation import evaluate_fitness
from src.fitness.swarm_fitness_diversity import swarm_fitness_diversity # noqa 401 note: if changed fitness, here import!
from src.operators.selection import selection
from src.operators.crossover import crossover
from src.operators.mutation import mutation
from src.operators.replacement import replacement
from src.swarm.bt import BTConstruct
from src.swarm.default_params import default_params

class Neighbourhood:
    def __init__(self, neighbourhood=None):
        if neighbourhood is None:
            self.neighbourhood = list() # matrix
            self.valid = False
            self.radius = 0
            self.center = None
            self.size = 0
        else:
            self.set_neighbourhood(neighbourhood)

    def __str__(self):
        s = "  "
        for i in range(len(self.neighbourhood)):
            s += str(i) + (" " if i < 10 else "")
        s += "\n"
        cnt_r = 0
        for r in self.neighbourhood:
            s += str(cnt_r) + (" " if cnt_r < 10 else "")
            cnt_r += 1
            for tile in r:
                if not tile:
                    s += "X" + " "
                else:
                    s += str(tile.type.value) + " "
            s += "\n"
        return s

    def set_neighbourhood(self, neighbourhood):
        self.neighbourhood = neighbourhood
        self.valid = True
        self.radius = len(self.neighbourhood) // 2
        self.center = (self.radius, self.radius)
        self.size = len(self.neighbourhood)

    def get(self, obj_type: types.ObjectType):
        cells_with_object = list()
        for row in self.neighbourhood:
            for cell in row:
                if cell:
                    if cell.type == obj_type:
                        cells_with_object.append(cell)

        return len(cells_with_object) > 0, cells_with_object



class Agent:
    def __init__(self, name, sense_radius=1, max_speed=1, color=QtCore.Qt.black):
        super(Agent, self).__init__()
        self.name = name
        self.type = ObjectType.AGENT
        self.position = None
        self.bt_wrapper = BTConstruct(None, self)
        self.sense_radius = sense_radius
        self.color = color
        self.neighbourhood = Neighbourhood()
        self.next_step = None
        self.goal = None
        self.inventory = list()
        self.dropping_item = None  # item that should be dropped
        self.backend = None
        self.max_speed = max_speed

        # agent.home_base = None  # why not, I say :)
    def setup(self):
        pass

    def step(self):
            # sense
            resp = self.backend.sense_object_neighbourhood(self)
            self.neighbourhood.set_neighbourhood(resp.neighbourhood)

            # act
            self.bt_wrapper.behaviour_tree.tick()
    def set_position(self, pos):
        self.position = list(pos)

    def pickUpReq(self, position):
        resp = self.backend.pick_up_req(self, position)
        if isinstance(resp, PickUpResp):
            if resp.pickedObj:
                self.inventory.append(resp.pickedObj)
                return True
            else:
                raise TimeoutError("Item picked up by another agent")
        else:
            raise TypeError("got response of another type when picking up object")

    def dropReq(self, item_type):
        resp = None
        for item in self.inventory:
            if item.type == item_type:
                self.dropping_item = item
                self.inventory.remove(item)
                position = None  # where to drop
                tiles_next_to = [self.neighbourhood.neighbourhood[self.sense_radius + 1][self.sense_radius + 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius + 1][self.sense_radius - 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius - 1][self.sense_radius + 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius - 1][self.sense_radius - 1]
                                 ]

                for tile in tiles_next_to:
                    if tile and tile.occupied and tile.object.type == ObjectType.HUB:
                        logging.debug("AGENT: dropping to HUB")
                        position = tile.position

                if not position:  # no hub nearby
                    for tile in tiles_next_to:
                        if tile and not tile.occupied:
                            position = tile.position
                if position:
                    resp = self.backend.drop_out_resp(self, DropReq(self.name, item_type, position) )
                else:
                    self.inventory.append(self.dropping_item)
                    self.dropping_item = None
        if resp:
            if isinstance(resp, DropResp):
                if resp.dropped:
                    self.dropping_item = None
                    return True
                else:
                    self.inventory.append(self.dropping_item)
                    self.dropping_item = None
                    return False
            else:
                raise TypeError("got response of another type when picking up object")
        else:
            return False

    def __repr__(self):
        return "Agent {} at {}".format(self.name, self.position)


class EvoAgent(Agent):
    """"
    Agent performing GE locally.
    """
    def __init__(self, name, sense_radius=1, max_speed=1, color=QtCore.Qt.black, exchange_prob=1, genome_storage_threshold=2):
        super().__init__(name, sense_radius, max_speed, color)
        self.genotype_storage_threshold = genome_storage_threshold
        self.individual = None # type Individual
        self.individuals = list()
        self.exchanged_individuals = dict()
        self.num_of_truly_exchanged_individuals = 0

        self.GE_params = dict(default_params)

        self.exchange_prob = exchange_prob


    def setup(self):
        self.init_GE()

    def init_GE(self):
        src.algorithm.parameters.load_params("parameters.txt", agent=self)

        src.algorithm.parameters.set_params(None, create_files=True, agent=self)

        for key in self.GE_params.keys():
            val = self.GE_params[key]
            try:
                val = eval(val)
            except:
                pass
            self.GE_params[key] = val
        #self.GE_params['FITNESS_FUNCTION'] = self.GE_params['FITNESS_FUNCTION']()
        individuals = initialisation(size=1, agent=self) # size of the population = 1
        individuals = evaluate_fitness(individuals, agent=self)
        # Assign the genome to the agent
        self.individuals = individuals
        self.individual = self.individuals[0] # first of the randomly generated solutions
        self.exchanged_individuals[self.name] = self.individual
        self.num_of_truly_exchanged_individuals += 1

        self.bt_wrapper.xmlstring = self.individual.phenotype
        self.bt_wrapper.bt_from_xml()

    def step(self):
        # todo exploration fitness and overall fitness - from junkOrExamples/agent.py.overall_fitness()
        # sense
        resp = self.backend.sense_object_neighbourhood(self)
        self.neighbourhood.set_neighbourhood(resp.neighbourhood)
        agents_present, neighbouring_agent_cells = self.neighbourhood.get(types.ObjectType.AGENT)
        if agents_present:
            for cell in neighbouring_agent_cells:
                if not cell.object.name in self.exchanged_individuals.keys():
                    neighbour_genome = cell.object.ask_for_genome()
                    # add the genome no matter if the neighbour was willing to share - it serves as an info about asking
                    self.exchanged_individuals[cell.object.name] = neighbour_genome
                    self.num_of_truly_exchanged_individuals += 1 if neighbour_genome else 0

        # act
        self.bt_wrapper.behaviour_tree.tick()


        #update
        if self.num_of_truly_exchanged_individuals >= self.genotype_storage_threshold:
            #logging.fatal("EVOLUTION OF {}".format(self.name))
            self.individuals = [self.exchanged_individuals[k] for k in self.exchanged_individuals.keys() if self.exchanged_individuals[k] is not None]
            # todo make genetic step over self.individuals
            # NOTE: copied and slightly changed code from ponyge/step.py/step()
            parents = selection(self.individuals, self)

            # Crossover parents and add to the new population.
            cross_pop = crossover(parents, self)
            # NOTE: brutálně neefektivní, tady dělám stromy, které ale vzápětí zahodím.
            # Mutate the new population.
            new_pop = mutation(cross_pop, self)
            # todo for every ind generate tree

            # Evaluate  the fitness of the new population.
            new_pop = evaluate_fitness(new_pop, self)

            # Replace the old population with the new population.
            self.individuals = replacement(new_pop, self.individuals, self)

            # Generate statistics for run so far
            self.individuals.sort(reverse=True)
            self.individual = self.individuals[0]
            self.individual.fitness = 0
            self.exchanged_individuals = dict()
            self.exchanged_individuals[self.name] = self.individual


    def ask_for_genome(self):
        if random.random() < self.exchange_prob:
            return self.individual.deep_copy()
        else:
            return None

