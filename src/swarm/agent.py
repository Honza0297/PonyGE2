    # General
import logging
import os
import random
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

# BT
import py_trees
from swarm.bt import BTConstruct

# simulation
from swarm.models import TileModel
from swarm.neighbourhood import Neighbourhood, LocalMap
from swarm.packets import *
from swarm.types import ObjectType

# GE
from swarm.default_params import default_params
import algorithm.parameters
from fitness.evaluation import evaluate_fitness
from operators.crossover import crossover
from operators.initialisation import initialisation
from operators.mutation import mutation
from operators.replacement import replacement
from operators.selection import selection
from representation.individual import Individual

# Other
from PyQt5 import QtCore
import math

if TYPE_CHECKING:
    from swarm.backend import TestBackend

class EvoAgent:
    """"
    Agent performing GE locally on its own.
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
        self.position_history = dict()  # Places which agent did visit = was onto them. Reset after genome change
        # according to aadesh, agents should be memory full(?)
        self.local_map: LocalMap = None # TODO make it full object with helping functions etc

        self.goal = None
        self.objects_of_interest = {}

        self.sense_radius = sense_radius
        self.max_speed = max_speed
        self.inventory = list()
        if init_position:
            self.set_position(init_position)

        # Help simulation variables
        self.neighbourhood = Neighbourhood()
        self.next_step = None
        self.dropping_item = None  # item that should be dropped
        self.backend: TestBackend = None
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
        self.exploration_fitness_coeff = {"a":2, "b":0.3}

        # Logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Misc
        self.param_file = params_file

        # Deprecated etc
        # agent.home_base = None

    def setup_logging(self):
        # Prepare logger - for stderr and file
        if not os.path.exists(f"../results/{self.GE_params['LOG_FOLDER']}"):
            os.makedirs(f"../results/{self.GE_params['LOG_FOLDER']}")

        file_formatter = logging.Formatter("%(levelname)s:%(message)s")
        file_handler = logging.FileHandler(filename=f"../results/{self.GE_params['LOG_FOLDER']}/{self.name}")
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
        """
        How agent is printed.
        """
        return f"Agent {self.name} at {self.position}"

    def setup(self):
        self.init_GE()
        self.setup_logging()
        self.local_map = LocalMap(self, self.backend.board_model.dimension)

    def init_GE(self):  # noqa
        # Init GE parameters
        algorithm.parameters.load_params(self.param_file, agent=self)
        algorithm.parameters.set_params(None, create_files=True, agent=self)

        for key in self.GE_params.keys():
            val = self.GE_params[key]
            try:
                val = eval(val)
            except Exception:  # If error arises here, change TypeError to Exception
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

        # Logging
        fitnesses = tuple(
            individual.fitness if (not individual.invalid and individual.fitness) else 0 for individual in individuals)
        non_zero_fitnesses = tuple(i for i in fitnesses if i)
        if fitnesses:
            avg_fitness = sum(fitnesses) / len(fitnesses)
            avg_nonzero_fitness = 0 if not non_zero_fitnesses else (sum(fitnesses) / len(non_zero_fitnesses))
            self.logger.debug(f"[LST_F] List of fitness values: {fitnesses}.")
            self.logger.debug(f"[AVG_F] Average fitness (incl. invalids): {avg_fitness}")
            self.logger.debug(f"[AVG_F] Average fitness (excl. invalids): {avg_nonzero_fitness}")
        ############

        #  Assign the best genome to the agent
        self.individuals = individuals
        if not self.individual or self.individual.invalid or self.individual.fitness <= self.individuals[0].fitness:
            self.logger.debug("[IND_CHG] Current individual changed (fitness {} -> {})".format(
                self.individual.fitness if self.individual else "nan", self.individuals[0].fitness))
            self.individual = self.individuals[0]  # first = best
            self.position_history = dict()
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
        Performed every simulation step. Three basic parts as from GEESE algo: SENSE, ACT and UPDATE.
        SENSE: perceive environment together with asking for genome from agents.
        ACT: perform one tick in behavior tree.
        UPDATE: perform evolution step, if enough genomes are gathered (or too long in bad behavior).
        """
        self.logger.info("--------------------------------")
        start_time = time.perf_counter()

        # SENSE()
        self.steps += 1
        self.steps_without_evolution += 1
        self.position_history[tuple(self.position)] = self.steps
        self.logger.info(f"[S{self.steps}] Step {self.steps}")
        self.logger.debug(f"[POS] Position: {self.position}")
        self.logger.debug(
            f"[SWE{self.steps_without_evolution}] Step without evolution {self.steps_without_evolution}")
        self.logger.debug(f"[F] Current fitness at the start: {self.individual.fitness}")
        self.logger.debug(f"[G] Goal: {self.goal}")
        self.logger.debug(f"[NS] Next step: {self.next_step}")
        # actually sense
        resp = self.backend.sense_object_neighbourhood(self)
        self.neighbourhood.set_neighbourhood(resp.neighbourhood)
        self.local_map.update(self.neighbourhood)
        self.logger.debug(f"[NEIGH] Neighbourhood: {self.neighbourhood}")
        self.logger.debug(f"[LM] Local map: {self.local_map}")

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
        self.logger.debug(f"[TREE] Tree: {py_trees.display.ascii_tree(self.bt_wrapper.behaviour_tree.root)}")
        self.logger.debug(f"[GENOME] {self.individual.genome}")
        self.bt_wrapper.behaviour_tree.tick()
        self.compute_fitness()
        self.logger.debug(f"[GOAL] Goal is: {self.goal}")

        # UPDATE()
        # If there is enough genomes to perform evolution AND current behavior was at least tried...
        if self.num_of_truly_exchanged_individuals >= self.genotype_storage_threshold and self.steps_without_evolution > self.GE_params["MIN_STEPS_WITHOUT_EVOLUTION"]:
            self.steps_without_evolution = 0
            self.logger.debug("[EVO] Performing evolution step")
            individuals = [self.exchanged_individuals[k] for k in self.exchanged_individuals.keys() if
                           self.exchanged_individuals[k] is not None]
            # TODO do the individuals have their fitness functions?
            self.individuals = individuals
            self.evolution_step(individuals)
            self.logger.debug("[EVO] Evolution step finished")
        # else if evolution was not performed for too long...
        elif self.steps_without_evolution > self.GE_params["MAX_STEPS_WITHOUT_EVOLUTION"]:
            self.logger.debug("[EVO] Reached MAX_STEPS_WITHOUT_EVOLUTION ({}), reinitialising genome (exchanged "
                              "genomes retained).".format(self.GE_params["MAX_STEPS_WITHOUT_EVOLUTION"]))
            self.steps_without_evolution = 0

            individuals = [self.exchanged_individuals[k] for k in self.exchanged_individuals.keys() if
                           self.exchanged_individuals[k] is not None]
            # It does not need to be exactly POPULATION_SIZE, but it is a good start (we just need some number of valid individuals)
            individuals += self._extend_population()
            self.individuals = individuals
            self.evolution_step(individuals)
            
        self.logger.debug(f"[F] Current fitness: {self.individual.fitness}")
        duration = time.perf_counter() - start_time
        self.logger.debug(f"[TIME] Step took {duration} s")

    def _extend_population(self):
        new_individuals = initialisation(size=self.GE_params["POPULATION_SIZE"]-self.num_of_truly_exchanged_individuals, agent=self)
        # Needing at least self.genotype_storage_threshold genomes to perform evolution:
        new_individuals = evaluate_fitness(new_individuals, self)
        valid_inds = [ind for ind in new_individuals if not ind.invalid]
        while len(valid_inds) < self.genotype_storage_threshold:
            new_individuals = [vi for vi in valid_inds] + initialisation(size=self.GE_params["POPULATION_SIZE"]-self.num_of_truly_exchanged_individuals, agent=self)
            valid_inds = [ind for ind in new_individuals if not ind.invalid]
        return valid_inds
    
    def evolution_step(self, individuals):
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
        self.logger.debug("[F] EX: {}, BT: {}, BETA*previous+current: {}".format(exploration_fitness, BT_feedback_fitness,
                                                                     self.individual.fitness))

    def compute_exploration_fitness(self):
        """
        Exploration fitness: number of locations/tiles visited
        """
        self.logger.debug(f"[HISTORY] Position history: {self.position_history}")
        exploration_fitness = 0
        if self.GE_params["EXPLORATION_FITNESS_FUNCTION"] == "linear":
            exploration_fitness = self._exploration_fitness_linear()
        elif self.GE_params["EXPLORATION_FITNESS_FUNCTION"] == "exponential":
            exploration_fitness = self._exploration_fitness_exponential()
        else:
            self.logger.error(f"Unknown exploration fitness function: {self.GE_params['EXPLORATION_FITNESS_FUNCTION']}")
        return exploration_fitness

    def _exploration_fitness_linear(self):
        """Exploration fitness: number of locations/tiles visited"""
        return len(self.position_history)
    
    def _exploration_fitness_exponential(self):
        """Exploration fitness: sum(a*e^(-steps_since_last_visit)*b)) across all visited locations/tiles"""
        return sum([self.exploration_fitness_coeff["a"]*math.e ** -((self.steps - self.position_history[k])*self.exploration_fitness_coeff["b"]) for k in self.position_history.keys()])
        
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

        if self.GE_params["PENALTY"]:
            selector_penalty = sum([-2 for sel in selectors if sel.status == py_trees.common.Status.FAILURE])
            postcond_penalty = sum([-2 for pcond in postcond if pcond.status == py_trees.common.Status.FAILURE])
        else:
            selector_penalty = 0
            postcond_penalty = 0
        
        return selectors_reward + postcond_reward + selector_penalty + postcond_penalty


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
                drop_position = None
                tiles_next_to = [self.neighbourhood.neighbourhood[self.sense_radius + 1][self.sense_radius + 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius + 1][self.sense_radius - 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius - 1][self.sense_radius + 1],
                                 self.neighbourhood.neighbourhood[self.sense_radius - 1][self.sense_radius - 1]
                                 ]
                # Preferably drop to hub
                for tile in tiles_next_to:
                    if tile and tile.occupied and tile.object.type == ObjectType.HUB:
                        self.logger.debug(f"[FH] Dropping food to HUB at {tile.position}")
                        drop_position = tile.position

                if not drop_position:  # no hub nearby
                    for tile in tiles_next_to:
                        if tile and not tile.occupied:
                            drop_position = tile.position

                if drop_position:
                    resp = self.backend.drop_out_resp(self, DropReq(self.name, item_type, drop_position))
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
