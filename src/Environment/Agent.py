

from Runtime import Runtime
from Direction import *

class Agent():
    def __init__(self, runtime: Runtime, position, name):
        self.name = name
        self.position = position
        self.runtime = runtime
        self.image = None
        pass

    def update_pos(self, direction):
        if direction == up:
            self.position[0] -= 1
        elif direction == down:
            self.position[0] += 1
        elif direction == left:
            self.position[1] -= 1
        elif direction == right:
            self.position[1] += 1

    def step(self):
        pass

    def sense(self):
        pass




