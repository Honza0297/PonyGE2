import logging
import queue
import random
import sys
import threading
import time

import py_trees.trees
from PyQt5 import QtCore

from src.swarm.types import ObjectType
from src.swarm.packets import *


class Neighbourhood:
    def __init__(self, neighbourhood=None):
        if neighbourhood is None:
            self.neighbourhood = list()
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


class Agent(threading.Thread):
    def __init__(self, name, sense_radius=1, color=QtCore.Qt.black):
        super(Agent, self).__init__()
        self.name = name
        self.type = ObjectType.AGENT
        self.request_queue = None
        self.position = None
        self.bt = None
        self.response_queue = queue.Queue()
        self.sense_radius = sense_radius
        self.color = color
        self.neighbourhood = Neighbourhood()
        self.next_step = None
        self.goal = None
        self.inventory = list()
        self.dropping_item = None  # item that should be dropped
        # agent.home_base = None  # why not, I say :)

    def set_queue(self, q):
        self.request_queue = q

    def sense(self):
        self.request_queue.put(Sense(self.name))

    def run(self):
        # Init its position
        init_msg = self.response_queue.get()
        self.position = list(init_msg.position)
        logging.debug("{}: Init position is  {}".format(self.name, self.position))
        while True:
            if not self.bt.root.status == py_trees.common.Status.RUNNING:
                logging.debug("{}: My root state is: {}".format(self.name, self.bt.root.status))
                self.sense()
                resp = self.response_queue.get()
                if resp.agent_name != self.name:
                    raise Exception("Bad message")
                self.neighbourhood.set_neighbourhood(resp.neighbourhood)
                print(self.neighbourhood)
            #print("before tick")
            self.bt.tick()
            #print("after_tick")
            time.sleep(0.1)

    def set_position(self, pos):
        self.position = list(pos)
    def pickUpReq(self, position):
        self.request_queue.put(PickUpReq(self.name, position))

    def dropReq(self, item_type):
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
                        position = tile.position

                if not position:  # no hub nearby
                    for tile in tiles_next_to:
                        if tile and not tile.occupied:
                            position = tile.position

                if position:
                    self.request_queue.put(DropReq(self.name, item_type, position))
                    return True
                else:
                    self.inventory.append(self.dropping_item)
                    self.dropping_item = None
                    return False
        return False

    def checkDropResp(self):
        try:
            resp = self.response_queue.get(block=False)
        except queue.Empty:
            return False

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

    def getPickedItem(self):
        resp = None
        try:
            resp = self.response_queue.get(block=False)
        except queue.Empty:
            return False

        if isinstance(resp, PickUpResp):
            if resp.pickedObj:
                self.inventory.append(resp.pickedObj)
                return True
            else:
                raise TimeoutError("Item picked up by another agent")
        else:
            raise TypeError("got response of another type when picking up object")

    def __repr__(self):
        return "Agent {} at {}".format(self.name, self.position)
