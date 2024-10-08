import cProfile
import os
import sys

import time
import logging
import threading
from typing import Optional

from swarm.agent import EvoAgent
from swarm.math import compute_distance
from swarm.models import BoardModel, TileModel
from swarm.packets import *
from swarm.objects import *
from swarm.types import ObjectType
import random

GENOME = [79242, 75288, 93946, 83682, 80172, 11178, 75654, 24507, 16904, 10288, 17401, 75438, 702, 37977, 15383, 32074, 97093, 85682, 80665, 6155, 92769, 19285, 19954, 8903, 52532, 16624, 72056, 20582, 50856, 52945, 95519, 77299, 34370, 19326, 48349, 70714, 51384, 8460, 32414, 52821, 36896, 43539, 2803, 12593, 78952, 84255, 90838, 86875, 44221, 59373]

class Backend(threading.Thread):
    def __init__(self, gui, level):
        super(Backend, self).__init__()
        self.gui = gui

        self.board_model: Optional[BoardModel] = None  # BoardModel(gui.dimension)
        self.agents = list()
        self.random = random

        self.step = False
        self.stop = True  # True if wait for buttons, False for autostart
        self.end = False  # When comes True, simulation will end
        self.restart = False

        # Logging
        self.logger = logging.getLogger("backend")
        self.logger.setLevel(level)

        # Simulation
        self.food_picked_history = []
        self.food_dropped_history = []
        self.fitness_history = []


    def setup(self):
        if not os.path.exists(f"../results/{self.agents[0].GE_params['LOG_FOLDER']}"):
            os.makedirs(f"../results/{self.agents[0].GE_params['LOG_FOLDER']}")

        try:
            os.symlink(f"../results/{self.agents[0].GE_params['LOG_FOLDER']}", f"../results/latest", target_is_directory=True)
        except FileExistsError:
            os.unlink(f"../results/latest")
            os.symlink(f"../results/{self.agents[0].GE_params['LOG_FOLDER']}", f"../results/latest", target_is_directory=True)

        file_formatter = logging.Formatter("%(levelname)s:%(message)s")
        file_handler = logging.FileHandler(
            filename=f"../results/{self.agents[0].GE_params['LOG_FOLDER']}/backend")
        file_handler.setLevel(self.logger.level)
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(file_handler)

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            agent.backend = self
            agent.setup()
            pass  # place for breakpoint
        else:
            raise KeyError("Agent name already registered: {}", agent.name)

    def update_gui(self):
        timer = threading.Timer(0.1, self.update_gui)
        timer.start()
        self.gui.update(self.board_model)

    def run(self):
        raise NotImplemented

    def place_object(self, obj: EnvironmentObject, position=None, rand=False):
        pos_ok = False
        if rand:
            while not pos_ok:
                position = [random.randint(0, self.board_model.dimension),
                            random.randint(0, self.board_model.dimension)]
                pos_ok = self.check_occupancy(position, obj.radius)
        else:
            pos_ok = self.check_occupancy(position, obj.radius)

        if not pos_ok:
            raise ValueError(
                f"Object {obj.type.value} of radius {obj.radius} cannot be placed at {position} due to occupancy.")
        for r in range(position[0] - obj.radius, position[0] + obj.radius + 1):
            for c in range(position[1] - obj.radius, position[1] + obj.radius + 1):
                if r < 0 or c < 0 or r >= self.board_model.dimension or c >= self.board_model.dimension:
                    continue
                tile = self.board_model.tiles[r][c]
                if compute_distance(tile.position, position) <= obj.radius:
                    tile.place_object(obj)
        obj.set_place(position, self.board_model)

    def check_occupancy(self, position, radius):
        pos_min = [position[0] - radius, position[1] - radius]
        pos_max = [position[0] + radius, position[1] + radius]
        for r in range(pos_min[0], pos_max[0]):
            for c in range(pos_min[1], pos_max[1]):
                if r < 0 or c < 0 or r >= self.board_model.dimension or c >= self.board_model.dimension:
                    continue
                tile = self.board_model.tiles[r][c]
                if compute_distance(position, tile.position) <= radius and tile.occupied:
                    return False
        return True


class TestBackend(Backend):
    def __init__(self, gui, deterministic=False, level=logging.DEBUG):
        super(TestBackend, self).__init__(gui, level)
        self.param_file = None
        self.deterministic = deterministic

    def setup(self):
        super().setup()

    def run(self):
        self.run_wrapper()
        # cProfile.runctx("self.run_wrapper()", globals(), locals(), "backend_stats_{}".format(time.time()))
        self.do_final_stats()
        print("End")
        sys.exit(0)

    def setup_simulation(self, num_of_agents, param_file, reset_gui=False):
        if reset_gui:
            self.gui.reset_board(self.gui.dimension)
        self.restart = False
        self.param_file = param_file

        self.board_model = BoardModel(self.gui.dimension)
        self.update_gui()
        for i in range(num_of_agents):

            """if i == 0:
                agent = EvoAgent("agent" + str(i), sense_radius=10, genome_storage_threshold=7, init_genome=GENOME,
                                 params_file=param_file, init_position=[6, 9])
            else:
                agent = EvoAgent("agent" + str(i), sense_radius=10, genome_storage_threshold=7, init_genome=None,
                                 params_file=param_file)"""

            agent = EvoAgent("agent" + str(i), sense_radius=10, genome_storage_threshold=7, init_genome=None,
                             params_file=param_file)

            self.register_agent(agent)
        #food = [FoodSource("jidlo" + str(random.randint(0, 100)), ObjectType.FOOD, 2) for _ in range(1)]
        food = FoodSource("jidlo", ObjectType.FOOD, 7)
        hub = Hub("hub", ObjectType.HUB, 10)

        self.place_object(hub, (self.board_model.dimension//2, self.board_model.dimension//2))
        #self.place_object(food, (5,5))
        self.place_object(food, (32, 32))
        self.update_gui()
        self.place_agents()
        self.update_gui()

    def do_final_stats(self):
        self.logger.debug("---------Final report----------")

        # Food
        self.logger.debug("[FOOD] Food dropped (agent, position, into base? (True/False)")
        number_of_food_inside_base = 0
        for line in self.food_dropped_history:
            self.logger.debug("{},{},{}".format(*line))
            number_of_food_inside_base += 1 if line[-1] else 0  # line[-1] = dropped inside base?
        self.logger.debug(f"[FOOD] Overall food inside base: {number_of_food_inside_base}")

        self.logger.debug("[FOOD] Food picked (agent, agent_position, food_position):")
        for line in self.food_picked_history:
            self.logger.debug("{},{},{}".format(*line))
        self.logger.debug(f"[FOOD] Overall food picked: {len(self.food_picked_history)}")

        # Overall fitness
        self.logger.debug("[FITNESS] Fitness functions over the steps (avg, best)")
        for idx, line in enumerate(self.fitness_history):
            self.logger.debug("{},{},{}".format(idx, *line))

        # Fitness: for every agent...
        #for agent in self.agents:
        #    self.logger.debug("Fitness stats")
        #    self.logger.debug(agent.make_final_stats())

        # TODO more final stats?

    def run_wrapper(self):
        cnt = 1
        self.setup()
        self.logger.debug(f"Number of agents: {len(self.agents)}")
        while True:
            if self.end:
                return
            if self.restart:
                self.do_final_stats()
                num_of_agents = len(self.agents)
                self.agents = []
                self.setup_simulation(num_of_agents, self.param_file, reset_gui=True)
                self.setup()
            if not self.stop:
                if self.step:
                    self.stop = True
                self.logger.debug(f"[S{cnt}] Step number {cnt}")
                step_start_time = time.perf_counter()

                # Stats
                fitnesses = tuple(agent.individual.fitness for agent in self.agents)
                best_fitness = max(fitnesses)
                idx_best = fitnesses.index(best_fitness)
                avg_fitness = sum(fitnesses) / len(fitnesses)
                self.fitness_history.append((avg_fitness, best_fitness))
                self.logger.debug(
                    f"[BST_F] Best fitness at the start: {best_fitness} ({self.agents[idx_best]})")
                self.logger.debug(f"[AVG_F] Average fitness at the start: {avg_fitness}")
                number_of_food_inside_base = len([line for line in self.food_dropped_history if line[-1]])
                self.logger.debug(f"[FOOD] Overall food dropped: {len(self.food_dropped_history)}")
                self.logger.debug(f"[FOOD] Overall food inside base: {number_of_food_inside_base}")
                self.logger.debug(f"[FOOD] Overall food picked: {len(self.food_picked_history)}")

                if not self.deterministic:
                    random.shuffle(
                        self.agents)  # change order every round to simulate non deterministic order of action for every agent
                    self.logger.debug(f"Agents order for this step: {[a.name[-1] for a in self.agents]}")
                for agent in self.agents:
                    if agent.name == "agent0":
                        pass  # NOTE just a place to control and observe one agent
                    agent.step()
                    self.gui.update(self.board_model)
                step_end_time = time.perf_counter()
                duration = step_end_time - step_start_time
                self.logger.debug(f"[TIME] Step {cnt} took {duration} s")
                if duration < 0.2:  # NOTE Arbitrary value to make the simulation reasonably slow
                    time.sleep(0.2 - duration)
                self.logger.info("---------------------------------------")
                cnt += 1
                """if cnt > 5:  # TODO oddelat stopku
                    self.stop = True
                    return"""
            else:
                time.sleep(0.2)

    def pick_up_req(self, agent, pos):
        tile = self.board_model.tiles[pos[0]][pos[1]]
        resp = PickUpResp(agent.name, None)
        self.logger.debug(f"[PCK] {agent.name} picks {tile.object} at {pos}")

        if tile and tile.object:
            if tile.type == ObjectType.HUB:
                raise TypeError(f"Agent at {agent.position} wants to grab hub at {tile.position}")

            resp = PickUpResp(agent.name, tile.object)
            tile.remove_object(tile.object)
            self.food_picked_history.append((agent.name, agent.position, pos))
        return resp

    def drop_out_resp(self, agent, req):
        resp = DropResp(agent.name, dropped=False)
        item_type = req.item_type
        pos = req.position
        self.logger.debug(f"[DRP] {agent.name} drops {item_type.value} at {pos}")
        cnd_tile_occupied = self.board_model.tiles[pos[0]][pos[1]].occupied
        cnd_food_to_hub = self.board_model.tiles[pos[0]][pos[1]].type == ObjectType.HUB and item_type == ObjectType.FOOD
        if not cnd_tile_occupied:
            if item_type == ObjectType.FOOD:
                new_object = FoodSource(name=f"food_dropped_by_{agent.name}", radius=0)
                new_object.set_place(pos, self.board_model)
                resp.dropped = True
            else:
                raise TypeError("This object cannot be dropped :)")
        elif cnd_tile_occupied and cnd_food_to_hub:  # item dropped to the base
            resp.dropped = True
            self.logger.info("{} dropped food to the base".format(agent.name, pos))
            # TODO maybe notify base that food arrived?
        self.food_dropped_history.append((agent.name, pos, cnd_food_to_hub))
        return resp

    def _randomly_place_object(self, agent):
        pos = None
        while True:
            pos = (
                random.randint(0, self.board_model.dimension - 1),
                random.randint(0, self.board_model.dimension - 1))
            tile = self.board_model.tiles[pos[0]][pos[1]]
            if not tile.occupied and tile.place_object(agent):
                # self.agents[agent_name].position = list(tile.position)
                break
            else:
                continue
        agent.set_position(pos)

    def place_agents(self):
        for agent in self.agents:
            if agent.position:
                if self.board_model.tiles[agent.position[0]][agent.position[1]].occupied:
                    self.logger.warning("{} wanted to be placed at {}, but position is occupied, replacing".format(
                        agent.name, agent.position))
                    agent.position = None
                    self._randomly_place_object(agent)
                else:
                    self.board_model.tiles[agent.position[0]][agent.position[1]].place_object(agent)
            else:
                self._randomly_place_object(agent)

    def sense_object_neighbourhood(self, obj):
        pos = obj.position
        radius = obj.sense_radius
        neighbourhood = list()
        for r in range(obj.position[0] - radius, obj.position[0] + radius + 1):
            row = list()
            for c in range(obj.position[1] - radius, obj.position[1] + radius + 1):
                # Supposing "circular" neighbourhood in square matrix -> some elements will be None:
                # NOTE If the board should be "infinite" with wrapping, use modulo to wrap the coordinates - here,
                #  in sense...

                #  1) test for out of the board/board overflow
                try:
                    tile = self.board_model.tiles[r][c]
                except IndexError:
                    tile = None

                # The same, but for "negative" AKA board underflow
                if r < 0 or c < 0:
                    tile = None

                if tile and abs(pos[0] - tile.position[0]) + abs(pos[1] - tile.position[1]) <= radius:
                    row.append(tile)
                else:
                    row.append(None)
            neighbourhood.append(row)
        msg = NeighbourhoodResp(obj.name, neighbourhood)
        return msg

    def move_agent(self, agent, old_position, new_position):
        # TODO check whether checks are present (AKA check whether agent can or cannot move to occupied location)
        # NOTE: they are not
        resp = Position(agent.name, agent.position)

        # CHECKS whether the movement is valid
        if new_position[0] < 0 or new_position[1] < 0 or new_position[0] >= self.board_model.dimension or new_position[1] >= self.board_model.dimension:
            raise RuntimeError(f"Attempted to move outside border (from {old_position} to {new_position}")
        if compute_distance(old_position, new_position) > agent.max_speed:
            raise ValueError("Desired distance greater than max speed")
        if list(old_position) != list(agent.position):
            raise RuntimeError("Agent does not know where it is.")

        if new_position[0] >= self.board_model.dimension or new_position[1] >= self.board_model.dimension:
            resp.position = agent.position
        elif not self.board_model.tiles[new_position[0]][new_position[1]].occupied:
            self.board_model.tiles[agent.position[0]][agent.position[1]].remove_object(agent)
            agent_placed = self.board_model.tiles[new_position[0]][new_position[1]].place_object(agent)
            if agent_placed:
                resp.position = new_position
                self.logger.debug(f"{agent.name} moved from {old_position} to {new_position}")
            else:
                raise RuntimeError(f"Agent {agent.name} not placed in desired location")
        else:
            resp.position = agent.position

        return resp
