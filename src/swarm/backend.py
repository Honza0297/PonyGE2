import queue
import random
import threading
import time
import logging

from src.swarm.math import compute_distance
from src.swarm.models import BoardModel, TileModel
from src.swarm.packets import *
from src.swarm.objects import *
from src.swarm.types import ObjectType

class Backend(threading.Thread):
    def __init__(self, gui):
        super(Backend, self).__init__()
        self.gui = gui

        self.board_model = BoardModel(gui.dimension)
        self.agents = dict()
        self.requestQueue = queue.Queue()

    def register_agent(self, agent):
        if agent.name not in self.agents.keys():
            self.agents[agent.name] = agent
            agent.set_queue(self.requestQueue)
        else:
            raise KeyError("Agent name already registered: {}", agent.name)

    def update_gui(self):
        timer = threading.Timer(1, self.update_gui)
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

    def run(self):
        cnt = 0
        self.place_agents()
        self.update_gui()
        for agent_name in self.agents.keys():
            self.agents[agent_name].start()
        while True:
            logging.debug("###########\nIteration number {}".format(cnt))
            cnt += 1
            self.update_gui()
            item = None
            try:
                item = self.requestQueue.get_nowait()
                logging.debug("BKN: Got item of type {}".format(type(item)))
            except queue.Empty:
                logging.debug("BKN: ReqQ empty")
                time.sleep(0.1)
                continue
            if type(item) == Sense:
                neighbourhood = self.sense_object_neighbourhood(self.agents[item.agent_name])
                self.agents[item.agent_name].response_queue.put(NeighbourhoodResp(item.agent_name, neighbourhood))
            elif type(item) == Move:
                logging.debug("BKN: Got request to move move from agent {}".format(item.agent_name))
                pos = self.move_agent(self.agents[item.agent_name], item.position)
                self.agents[item.agent_name].response_queue.put(Position(item.agent_name, pos))
                # TODO this is a bad practice! but we need the agent to be moved BEFORE its turn
                self.agents[item.agent_name].set_position(pos)
            elif type(item) == PickUpReq:
                pos = item.position
                tile = self.board_model.tiles[pos[0]][pos[1]]
                if tile.object:
                    resp = PickUpResp(item.agent_name, tile.object)
                    tile.remove_object(tile.object)
                    self.agents[item.agent_name].response_queue.put(resp)
            elif type(item) == DropReq:
                pos = item.position
                dropped = False
                if not self.board_model.tiles[pos[0]][pos[1]].occupied:
                    if item.item_type == ObjectType.FOOD:
                        new_object = FoodSource(name="food_dropped_by_{}".format(item.agent_name), radius=0)
                        new_object.set_place(pos, self.board_model)
                        dropped = True
                    else:
                        raise TypeError("This object cannot be dropped :)")
                resp = DropResp(item.agent_name, dropped)
                self.agents[item.agent_name].response_queue.put(resp)
            else:
                pass

    def place_agents(self):
        for agent_name in self.agents.keys():
            pos = None
            while True:
                pos = (
                random.randint(0, self.board_model.dimension - 1), random.randint(0, self.board_model.dimension - 1))
                # TODO workaround
                pos = (2, 6)
                tile = self.board_model.tiles[pos[0]][pos[1]]
                if not tile.occupied:
                    if tile.place_object(self.agents[agent_name]):
                        #self.agents[agent_name].position = list(tile.position)
                        break
                    else: continue
                else: continue
            self.agents[agent_name].response_queue.put(Position(agent_name, pos))

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
        return neighbourhood

    def move_agent(self, agent, position):
        retval = agent.position
        logging.debug("BKN: tries to move agent from {} to {}".format(agent.position, position))
        if not self.board_model.tiles[position[0]][position[1]].occupied:
            self.board_model.tiles[agent.position[0]][agent.position[1]].remove_object(agent)
            self.board_model.tiles[position[0]][position[1]].place_object(agent)
            retval = position
            logging.debug("BKN: Agent {} moved to {}".format(agent.name, agent.position))
        else:
            retval = agent.position

        return retval
