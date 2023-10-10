import os
import random
import sys
import logging

import py_trees
from PyQt5 import QtCore

from src.swarm import types
from src.swarm.neighbourhood import Neighbourhood
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
from src.representation.individual import Individual


class Agent:
    def __init__(self, name, sense_radius=1, max_speed=1, color=QtCore.Qt.black, level=logging.DEBUG):
        super(Agent, self).__init__()
        # Basic agent properties
        self.name = name
        self.type = ObjectType.AGENT
        self.color = color

        # Simulation properties
        self.position = None
        self.sense_radius = sense_radius
        self.max_speed = max_speed
        self.neighbourhood = Neighbourhood()
        self.next_step = None
        self.inventory = list()
        self.dropping_item = None  # item that should be dropped
        self.backend = None
        self.goal = None
        self.steps = 0
        self.steps_without_evolution = 0

        # BT props
        self.bt_wrapper = BTConstruct(None, self)

        # GE props
        self.GE_params = dict(default_params)

        # Logging stuff
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Deprecated etc
        # agent.home_base = None

    def setup(self):
        # Prepare logger - for stderr and file
        if not os.path.exists("../results/{}".format(self.GE_params["LOG_FOLDER"])):
            os.makedirs("../results/{}".format(self.GE_params["LOG_FOLDER"]))

        file_formatter = logging.Formatter("%(levelname)s:%(message)s")
        file_handler = logging.FileHandler(filename="../results/{}/{}".format(self.GE_params["LOG_FOLDER"], self.name))
        file_handler.setLevel(self.logger.level)
        file_handler.setFormatter(file_formatter)

        # For some reason, it logs even without streamhandler
        """stream_formatter = logging.Formatter(self.name+":%(levelname)s:%(message)s")
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setLevel(self.logger.level)
        stream_handler.setFormatter(stream_formatter)"""

        self.logger.addHandler(file_handler)
        #self.logger.addHandler(stream_handler)

        # TODO two handlers: one for std and one for file
        # TODO formatter(s)?

    def step(self):
        raise NotImplemented

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
    def __init__(self, name, sense_radius=1, max_speed=1, color=QtCore.Qt.black, exchange_prob=1, genome_storage_threshold=2, init_genome=None, params_file="parameters.txt"):
        super().__init__(name, sense_radius, max_speed, color)
        self.genotype_storage_threshold = genome_storage_threshold
        self.individual = None # type Individual
        self.individuals = list()
        self.exchanged_individuals = dict()
        self.num_of_truly_exchanged_individuals = 0

        #self.GE_params = dict(default_params)
        self.param_file = params_file
        self.init_genome = init_genome
        self.exchange_prob = exchange_prob
        self.visited_locations = set()


    def setup(self):
        self.init_GE()
        super().setup()

    def init_GE(self):
        src.algorithm.parameters.load_params(self.param_file, agent=self)

        src.algorithm.parameters.set_params(None, create_files=True, agent=self)

        for key in self.GE_params.keys():
            val = self.GE_params[key]
            try:
                val = eval(val)
            except:
                pass
            self.GE_params[key] = val
        #self.GE_params['FITNESS_FUNCTION'] = self.GE_params['FITNESS_FUNCTION']()
        if self.init_genome:
            individuals = [Individual(genome=self.init_genome, ind_tree=None, agent=self)]
        else:
            individuals = initialisation(size=10, agent=self) # size of the population = 10
        individuals = evaluate_fitness(individuals, agent=self)
        individuals.sort(reverse=True)
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
        self.visited_locations.add(tuple(self.position))
        self.steps += 1
        self.steps_without_evolution += 1
        self.logger.debug("In step")
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

        self.compute_fitness()

        #update
        # noinspection PyTypeChecker
        if self.num_of_truly_exchanged_individuals >= self.genotype_storage_threshold:
            self.steps_without_evolution = 0
            #logging.fatal("EVOLUTION OF {}".format(self.name))
            individuals = [self.exchanged_individuals[k] for k in self.exchanged_individuals.keys() if self.exchanged_individuals[k] is not None]
            # todo make genetic step over self.individuals
            # NOTE: copied and slightly changed code from ponyge/step.py/step()
            parents = selection(individuals, self)

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
            self.num_of_truly_exchanged_individuals = 1

            self.bt_wrapper.xmlstring = self.individual.phenotype
            self.bt_wrapper.bt_from_xml()


        elif self.steps_without_evolution > self.GE_params["MAX_STEPS_WITHOUT_EVOLUTION"]:
            self.steps_without_evolution = 0

            individuals = initialisation(size=10, agent=self)  # size of the population = 10
            individuals = evaluate_fitness(individuals, agent=self)
            individuals.sort(reverse=True)
            # Assign the genome to the agent
            self.individuals = individuals
            self.individual = self.individuals[0]  # first of the randomly generated solutions
            self.exchanged_individuals[self.name] = self.individual
            self.num_of_truly_exchanged_individuals += 1

            self.bt_wrapper.xmlstring = self.individual.phenotype
            self.bt_wrapper.bt_from_xml()

    def ask_for_genome(self):
        if random.random() < self.exchange_prob:
            return self.individual.deep_copy()
        else:
            return None

    def compute_fitness(self):
        exploration_fitness = self.compute_exploration_fitness()
        BT_feedback_fitness = self.compute_BT_feedback_fitness()
        self.individual.fitness = self.GE_params["BETA"]*self.individual.fitness + exploration_fitness + BT_feedback_fitness


    def compute_exploration_fitness(self):
        return max(len(self.visited_locations), 0)

    def compute_BT_feedback_fitness(self):
        all_nodes = list(self.bt_wrapper.behaviour_tree.root.iterate())
        selectors = list(filter(
            lambda x: isinstance(x, py_trees.composites.Selector), all_nodes)
        )

        postcond = list(filter(
            lambda x: x.name.split('_')[-1] == 'postcond', all_nodes)
        )

        selectors_reward = sum([1 for sel in selectors if sel.status == py_trees.common.Status.SUCCESS])
        postcond_reward = sum([1 for pcond in postcond if pcond.status == py_trees.common.Status.SUCCESS])

        return selectors_reward+postcond_reward
