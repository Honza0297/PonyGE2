# General
import logging
import os
import random
import time
from typing import Dict, Any

# BT
import py_trees
from src.swarm.bt import BTConstruct
from src.swarm.default_params import default_params
from src.swarm.neighbourhood import Neighbourhood
from src.swarm.packets import *
from src.swarm.types import ObjectType

# GE
import src.algorithm.parameters
from src.fitness.evaluation import evaluate_fitness
from src.operators.crossover import crossover
from src.operators.initialisation import initialisation
from src.operators.mutation import mutation
from src.operators.replacement import replacement
from src.operators.selection import selection
from src.representation.individual import Individual

# Other
from PyQt5 import QtCore


class EvoAgent:
    """"
    Agent performing GE locally.
    """
    GE_params: dict[str | Any, str | int | None | Any]

    def __init__(self, name, sense_radius=1, max_speed=1, color=QtCore.Qt.black, level=logging.DEBUG, exchange_prob=1,
                 genome_storage_threshold=2, init_genome=None, params_file="parameters.txt", init_position=None):

        # Basic agent properties
        self.name = name
        self.type = ObjectType.AGENT
        self.color = color

        # Simulation
        self.position = None
        # Places which agent did visit = was next to it. Reseted every time new behavior is adopted:
        self.position_history = set()
        self.place_types_visited = {ObjectType.FOOD: False, ObjectType.HUB: False}

        self.sense_radius = sense_radius
        self.max_speed = max_speed
        self.inventory = list()
        if init_position:
            self.set_position(init_position)

        # Help simulation variables
        self.neighbourhood = Neighbourhood()
        self.next_step = None
        self.dropping_item = None  # item that should be dropped
        self.backend = None
        self.steps = 0
        self.steps_without_evolution = 0
        self.heading = None

        # BT variables
        self.bt_wrapper = BTConstruct(None, self)

        # GE
        self.GE_params = dict(default_params)
        self.init_genome = init_genome
        self.genotype_storage_threshold = genome_storage_threshold
        self.individual = None  # type Individual
        self.exchange_prob = exchange_prob
        self.individuals = list()
        self.exchanged_individuals = dict()
        self.num_of_truly_exchanged_individuals = 0

        # Logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Misc
        self.param_file = params_file

        # Deprecated etc
        # agent.home_base = None

    def setup_logging(self):
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
        # self.logger.addHandler(stream_handler)

    def __repr__(self):
        return "Agent {} at {}".format(self.name, self.position)

    def setup(self):
        self.init_GE()
        self.setup_logging()

    def init_GE(self):
        # Init GE parameters
        src.algorithm.parameters.load_params(self.param_file, agent=self)
        src.algorithm.parameters.set_params(None, create_files=True, agent=self)

        for key in self.GE_params.keys():
            val = self.GE_params[key]
            try:
                val = eval(val)
            except:
                pass
            self.GE_params[key] = val

        if self.init_genome:
            individuals = [Individual(genome=self.init_genome, ind_tree=None, agent=self)]
            for ind in individuals:
                ind.evaluate()
            self.choose_new_individual(individuals)

        else:
            change_ok = False
            while not change_ok:
                individuals = initialisation(size=self.GE_params["POPULATION_SIZE"], agent=self)
                individuals = evaluate_fitness(individuals, self)
                change_ok = self.choose_new_individual(individuals)

    def choose_new_individual(self, individuals):
        individuals.sort(reverse=True)

        fitnesses = tuple(
            individual.fitness if (not individual.invalid and individual.fitness) else 0 for individual in individuals)
        non_zero_fitnesses = tuple(i for i in fitnesses if i)
        if fitnesses:
            avg_fitness = sum(fitnesses) / len(fitnesses)
            avg_nonzero_fitness = 0 if not non_zero_fitnesses else (sum(fitnesses) / len(non_zero_fitnesses))
            self.logger.debug("[LST_F] List of fitness values: {}.".format(fitnesses))
            self.logger.debug("[AVG_F] Average fitness (incl. invalids): {}".format(avg_fitness))
            self.logger.debug("[AVG_F] Average fitness (excl. invalids): {}".format(avg_nonzero_fitness))

        #  Assign the best genome to the agent
        self.individuals = individuals
        if not self.individual or self.individual.invalid or self.individual.fitness <= self.individuals[0].fitness:
            self.logger.debug("[IND_CHG] Current individual changed (fitness {} -> {})".format(
                self.individual.fitness if self.individual else "nan", self.individuals[0].fitness))
            self.individual = self.individuals[0]  # first = best
            self.place_types_visited = {"food": False, "hub": False}  # Reset memory when new behavior is chosen
            self.position_history = set()
        else:
            self.logger.debug("[IND_CHG] Current individual not changed.")


        # In case new individual will be invalid, return False to notify layer above something is wrong
        if self.individual.invalid:
            return False

        # Exchange genome with itself :)
        self.exchanged_individuals = {self.name: self.individual}
        self.num_of_truly_exchanged_individuals = 1

        # Prepare BT
        self.bt_wrapper.xmlstring = self.individual.phenotype
        self.bt_wrapper.bt_from_xml()
        return True

    def make_final_stats(self):
        # TODO :)
        # Určitě logovat historii fitness funkcí
        return "Not now"

    def step(self):
        """
        Performed every simulation step. Three basic parts as from GEESE algo: SENSE, ACT and UPDATE
        """
        self.logger.info("--------------------------------")
        start_time = time.perf_counter()

        # SENSE()
        self.steps += 1
        self.steps_without_evolution += 1
        self.position_history.add(tuple(self.position))
        self.logger.info("[S{}] Step {}".format(self.steps, self.steps))
        self.logger.debug("[POS] Position: {}".format(self.position))
        self.logger.debug(
            "[SWE{}] Step without evolution {}".format(self.steps_without_evolution, self.steps_without_evolution))
        self.logger.debug("[F] Current fitness at the start: {}".format(self.individual.fitness))
        # actually sense
        resp = self.backend.sense_object_neighbourhood(self)
        self.neighbourhood.set_neighbourhood(resp.neighbourhood)
        self.check_for_newly_visited_object_types()

        # Try to exchange genomes
        agents_present, neighbouring_agent_cells = self.neighbourhood.get(ObjectType.AGENT)
        if agents_present:
            for cell in neighbouring_agent_cells:
                if cell.object.name not in self.exchanged_individuals.keys():
                    neighbour_genome = cell.object.ask_for_genome()
                    # add the genome no matter if the neighbour was willing to share - it serves as an info about asking
                    self.exchanged_individuals[cell.object.name] = neighbour_genome
                    self.num_of_truly_exchanged_individuals += 1 if neighbour_genome else 0

        # ACT()
        # actually act
        self.logger.debug("[TREE] Tree: {}".format(py_trees.display.ascii_tree(self.bt_wrapper.behaviour_tree.root)))
        self.logger.debug("[GENOME] {}".format(self.individual.genome))
        self.bt_wrapper.behaviour_tree.tick()
        self.compute_fitness()

        # UPDATE()
        # If there is enough genomes to perform evolution...
        if self.num_of_truly_exchanged_individuals >= self.genotype_storage_threshold:
            self.steps_without_evolution = 0
            self.logger.debug("[EVO] Performing evolution step")
            individuals = [self.exchanged_individuals[k] for k in self.exchanged_individuals.keys() if
                           self.exchanged_individuals[k] is not None]

            # NOTE: below is copied and slightly changed code from ponyge/step.py/step()
            # no new individuals created, just parents chosen
            parents = selection(individuals, self)

            # Crossover parents and add to the new population.
            cross_pop = crossover(parents, self)

            # Mutate the new population.
            new_pop = mutation(cross_pop, self)

            # NOTE: Here, attribute grammar gets involved
            for ind in new_pop:
                ind.perform_attribute_check()

            # Evaluate  the fitness of the new population.
            new_pop = evaluate_fitness(new_pop, self)

            # Replace the old population with the new population.
            individuals = replacement(new_pop, self.individuals, self)

            self.choose_new_individual(individuals)
            self.logger.debug("[EVO] Evolution step finished")
        # else if evolution was not performed for too long...
        elif self.steps_without_evolution > self.GE_params["MAX_STEPS_WITHOUT_EVOLUTION"]:
            self.logger.debug("[EVO] Reached MAX_STEPS_WITHOUT_EVOLUTION ({}), reinitialising genome (exchanged "
                              "genomes retained).".format(self.GE_params["MAX_STEPS_WITHOUT_EVOLUTION"]))
            self.steps_without_evolution = 0

            individuals = initialisation(size=10, agent=self)  # size of the population = 10
            evaluate_fitness(individuals)
            self.choose_new_individual(individuals)

        self.logger.debug("[F] Current fitness: {}".format(self.individual.fitness))
        duration = time.perf_counter() - start_time
        self.logger.debug("[TIME] Step took {} s".format(duration))

    def ask_for_genome(self):
        """
        This function is called by another agents trying to acquire this agent's genome
        """
        if random.random() < self.exchange_prob and not self.individual.invalid:
            return self.individual.deep_copy()
        else:
            return None

    def compute_fitness(self):
        """
        Computes fitness A(t) in current time step t using the formula A(t) = beta*A(t-1)+ exploration_fitness + bt_feedback fitness
        """
        exploration_fitness = self.compute_exploration_fitness()
        BT_feedback_fitness = self.compute_BT_feedback_fitness()
        self.individual.fitness = self.GE_params[
                                      "BETA"] * self.individual.fitness + exploration_fitness + BT_feedback_fitness
        self.logger.debug("[FITNESS] EX: {}, BT: {}, sum: {}".format(exploration_fitness, BT_feedback_fitness, self.individual.fitness))

    def compute_exploration_fitness(self):
        """
        Exploration fitness: number of locations/tiles visited
        """
        self.logger.debug("[HISTORY] Position history: {}".format(self.position_history))
        return max(len(self.position_history), 0)

    def compute_BT_feedback_fitness(self):
        """
        details n fitness/swarm_diversity.py (or something like that) in PonyGE2
        """
        all_nodes = list(self.bt_wrapper.behaviour_tree.root.iterate())
        selectors = list(filter(
            lambda x: isinstance(x, py_trees.composites.Selector), all_nodes)
        )

        postcond = list(filter(
            lambda x: x.name.split('_')[-1] == 'PostCnd', all_nodes)
        )

        selectors_reward = sum([1 for sel in selectors if sel.status == py_trees.common.Status.SUCCESS])
        postcond_reward = sum([1 for pcond in postcond if pcond.status == py_trees.common.Status.SUCCESS])

        return selectors_reward + postcond_reward

    def check_for_newly_visited_object_types(self):
        center = self.neighbourhood.center
        if self.neighbourhood.neighbourhood[center[0] + 1][center[1] + 1] and \
           self.neighbourhood.neighbourhood[center[0] + 1][center[1] + 1].occupied:
            self.place_types_visited[self.neighbourhood.neighbourhood[center[0] + 1][center[1] + 1].object.type] = True

        if self.neighbourhood.neighbourhood[center[0] - 1][center[1] + 1] and \
           self.neighbourhood.neighbourhood[center[0] - 1][center[1] + 1].occupied:
            self.place_types_visited[self.neighbourhood.neighbourhood[center[0] - 1][center[1] + 1].object.type] = True

        if self.neighbourhood.neighbourhood[center[0] + 1][center[1] - 1] and \
           self.neighbourhood.neighbourhood[center[0] + 1][center[1] - 1].occupied:
            self.place_types_visited[self.neighbourhood.neighbourhood[center[0] + 1][center[1] - 1].object.type] = True

        if self.neighbourhood.neighbourhood[center[0] - 1][center[1] - 1] and \
           self.neighbourhood.neighbourhood[center[0] - 1][center[1] - 1].occupied:
            self.place_types_visited[self.neighbourhood.neighbourhood[center[0] - 1][center[1] - 1].object.type] = True

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
                        self.logger.debug("[FH] Dropping food to HUB at {}".format(tile.position))
                        position = tile.position

                if not position:  # no hub nearby
                    for tile in tiles_next_to:
                        if tile and not tile.occupied:
                            position = tile.position
                if position:
                    resp = self.backend.drop_out_resp(self, DropReq(self.name, item_type, position))
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
