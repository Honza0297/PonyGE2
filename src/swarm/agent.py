import queue
import random
import sys
import threading
import time

from src.swarm.packets import *

class BasicAgent(threading.Thread):
    def __init__(self, name, sense_radius=1):
        super().__init__()
        self.name = name
        self.request_queue = None
        self.position = None
        self.bt = None
        self.response_queue = queue.Queue()
        self.sense_radius = sense_radius



    def set_queue(self, q):
        self.queue = q


class DummyAgent(threading.Thread):
    def __init__(self, name, sense_radius=1):
        super(DummyAgent, self).__init__()
        self.name = name
        self.request_queue = None
        self.position = None
        self.bt = None
        self.response_queue = queue.Queue()
        self.sense_radius = sense_radius

    def set_queue(self, q):
        self.request_queue = q

    def sense(self):
        self.request_queue.put(Sense(self.name))

    def run(self):
        #Init its position
        init_msg = self.response_queue.get()
        self.position = list(init_msg.position)
        print("Init position is  {}".format(self.position))
        while True:
            print("Agent {} starts its iteration".format(self.name))
            self.sense()
            resp = self.response_queue.get()
            print("Agent {} got sense response".format(self.name))
            #print("{}, {}, ".format(self.name, resp.agent_name))
            if resp.agent_name != self.name:
                raise Exception("Bad message")
            succ = self.random_move(resp.neighbourhood)
            print("Agent {} finished random move fction with succ = {}".format(self.name, succ))

            time.sleep(1)


    def random_move(self, neighbourhood):
        axis = random.randint(0, 1)
        offset = random.randint(0,1)*2-1  # 0/1 -> 0/2 -> -1/1
        new_pos = list(self.position)  # We need to deep copy
        new_pos[axis] += offset

        new_pos_in_neighbourhood = [self.sense_radius, self.sense_radius]
        new_pos_in_neighbourhood[axis] += offset
        print("Agent {} wants to move from {} to {}".format(self.name, self.position, new_pos))
        if neighbourhood[new_pos_in_neighbourhood[0]][new_pos_in_neighbourhood[1]] \
                and not neighbourhood[new_pos_in_neighbourhood[0]][new_pos_in_neighbourhood[1]].occupied:
            print("Agent {} putting move request".format(self.name))
            self.request_queue.put(Move(self.name, new_pos))
            resp = self.response_queue.get()
            if self.position == resp.position:
                print("Agent {} got wrong move response".format(self.name))
            self.position = list(resp.position)
            return True
        else: return False

    def __repr__(self):
        return "Agent {} at {}".format(self.name, self.position)