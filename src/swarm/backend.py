import queue
import random
import time
import logging
import threading
from src.swarm.math import compute_distance
from src.swarm.models import BoardModel, TileModel
from src.swarm.packets import *
from src.swarm.objects import *
from src.swarm.types import ObjectType
import random

class Backend(threading.Thread):
    def __init__(self, gui):
        super(Backend, self).__init__()
        self.gui = gui

        self.board_model = BoardModel(gui.dimension)
        self.agents = list()
        self.random = random

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            agent.backend = self
            agent.setup()
        else:
            raise KeyError("Agent name already registered: {}", agent.name)

    def update_gui(self):
        timer = threading.Timer(0.1, self.update_gui)
        timer.start()
        self.gui.update(self.board_model)

    def run(self):
        pass

    def place_object(self, obj: EnvironmentObject, position):
        for r in range(position[0]-obj.radius, position[0]+obj.radius+1):
            for c in range(position[1] - obj.radius, position[1] + obj.radius + 1):
                tile = self.board_model.tiles[r][c]
                if compute_distance(tile.position, position) <= obj.radius:
                    tile.place_object(obj)
        obj.set_place(position, self.board_model)


class TestBackend(Backend):
    def __init__(self, gui):
        super(TestBackend, self).__init__(gui)
    def setup(self):
        self.place_agents()
        self.update_gui()

    def run(self):
        cnt = 0
        self.setup()
        while True:
            logging.debug("###########\nIteration number {}".format(cnt))
            cnt += 1
            random.shuffle(self.agents)  # change order every round to simulate non deterministic order of action for every agent
            #self.gui.update(self.board_model)
            for agent in self.agents:
                agent.step()
                agent.bt_wrapper.visualize()
            time.sleep(0.2)

    def pick_up_req(self, agent, pos):
        tile = self.board_model.tiles[pos[0]][pos[1]]
        resp = PickUpResp(agent.name, None)

        if tile and tile.object:
            resp = PickUpResp(agent.name, tile.object)
            tile.remove_object(tile.object)
        return resp

    def drop_out_resp(self, agent, req):
        resp = DropResp(agent.name, dropped=False)
        item_type = req.item_type
        pos = req.position
        if not self.board_model.tiles[pos[0]][pos[1]].occupied:
            if item_type == ObjectType.FOOD:
                new_object = FoodSource(name="food_dropped_by_{}".format(agent.name), radius=0)
                new_object.set_place(pos, self.board_model)
                resp.dropped = True
            else:
                raise TypeError("This object cannot be dropped :)")
        elif self.board_model.tiles[pos[0]][pos[1]].occupied and self.board_model.tiles[pos[0]][pos[1]].type == ObjectType.HUB: # item dropped to the base
            resp.dropped = True
            logging.debug("BKN: Food was dropped to the base")
            # TODO maybe notify base that food arrived?
        return resp

    def place_agents(self):
        for agent in self.agents:
            pos = None
            while True:
                pos = (
                random.randint(0, self.board_model.dimension - 1), random.randint(0, self.board_model.dimension - 1))
                tile = self.board_model.tiles[pos[0]][pos[1]]
                if not tile.occupied:
                    if tile.place_object(agent):
                        #self.agents[agent_name].position = list(tile.position)
                        break
                    else: continue
                else: continue
            agent.set_position(pos)

    def sense_object_neighbourhood(self, obj):
        pos = obj.position
        radius = obj.sense_radius
        neighbourhood = list()
        for r in range(obj.position[0]-radius, obj.position[0]+radius+1):
            row = list()
            for c in range(obj.position[1]-radius, obj.position[1]+radius+1):
                # Supposing "circular" neighbourhood in square matrix -> some elements will be None:
                # TODO If the board should be "infinite" with wrapping, use modulo to wrap the coordinates - here,
                #  in sense...

                #  1) test for out of the board/board overflow
                try:
                    tile = self.board_model.tiles[r][c]
                except IndexError:
                    tile = None

                # The same, but for "negative" AKA board underflow
                if r < 0 or c < 0:
                    tile = None

                if tile and abs(pos[0]-tile.position[0])+abs(pos[1]-tile.position[1]) <= radius:
                    row.append(tile)
                else: row.append(None)
            neighbourhood.append(row)
        msg = NeighbourhoodResp(obj.name, neighbourhood)
        return msg

    def move_agent(self, agent, old_position, new_position):
        resp = Position(agent.name, agent.position)
        if compute_distance(old_position, new_position) > agent.max_speed:
            raise ValueError("Desired distance greater than max speed")
        if list(old_position) != list(agent.position):
            raise RuntimeError("Agent does not know where it is.")

        logging.debug("BKN: tries to move agent from {} to {}".format(agent.position, new_position))
        if not self.board_model.tiles[new_position[0]][new_position[1]].occupied:
            self.board_model.tiles[agent.position[0]][agent.position[1]].remove_object(agent)
            agent_placed = self.board_model.tiles[new_position[0]][new_position[1]].place_object(agent)
            if agent_placed:
                resp.position = new_position
                logging.debug("BKN: Agent {} moved to {}".format(agent.name, new_position))
            else:
                raise RuntimeError("Agent {} not placed in desired location".format(agent.name))
        else:
            resp.position = agent.position

        return resp

