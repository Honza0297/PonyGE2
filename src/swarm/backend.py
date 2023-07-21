import queue
import random
import threading
import time

from src.swarm.models import BoardModel
from src.swarm.packets import *

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
            print("Backend does its job: {}".format(cnt))
            cnt += 1
            self.update_gui()
            item = None
            try:
                item = self.requestQueue.get_nowait()
                print("Got item of type {}".format(type(item)))
            except queue.Empty:
                print("ReqQ empty")
                time.sleep(0.1)
                continue
            if type(item) == Sense:
                neighbourhood = self.get_object_neighbourhood(self.agents[item.agent_name])
                self.agents[item.agent_name].response_queue.put(Neighbourhood(item.agent_name, neighbourhood))
            elif type(item) == Move:
                print("##################got move from {}".format(item.agent_name))
                pos = self.move_agent(self.agents[item.agent_name], item.position)
                print("dddd")
                self.agents[item.agent_name].response_queue.put(Position(item.agent_name, pos))
                print("Ddd")
            else:
                pass

    def place_agents(self):
        for agent_name in self.agents.keys():
            pos = None
            while True:
                pos = (
                random.randint(0, self.board_model.dimension - 1), random.randint(0, self.board_model.dimension - 1))
                tile = self.board_model.tiles[pos[0]][pos[1]]
                if not tile.occupied:
                    if tile.place_object(self.agents[agent_name]):
                        #self.agents[agent_name].position = list(tile.position)
                        break
                    else: continue
                else: continue
            self.agents[agent_name].response_queue.put(Position(agent_name, pos))

    def get_object_neighbourhood(self, obj):
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
        print("#########backend tries to move agent from {} to {}".format(agent.position, position))
        if not self.board_model.tiles[position[0]][position[1]].occupied:
            self.board_model.tiles[agent.position[0]][agent.position[1]].remove_object(agent)
            self.board_model.tiles[position[0]][position[1]].place_object(agent)
        else: return agent.position
        return position
