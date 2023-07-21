# -*- coding: utf-8 -*-
"""
The agent class for swarm framework.

Core Objects: Agent
Authors: Aadesh Neupane, Jan Beran
"""


class Agent:
    """Base class for a agent."""

    def __init__(self, name, runtime):
        """Create a new agent.

        Overload this method to define diverse agents.
        Args:
            name: a unique name for the agent. It helps to
                  distingush between different agents in the environment.

            runtime: model class which gives the agent access to environmental
                    variables like sites, hub, food and others

        Attributes:
            capacity: agent's capacity to do some work in the environment

            attached_objects: a list which stores the objects attached
                               to the agent. Useful for carrying and droping
                               objects
        """
        self.name = name
        self.runtime = runtime
        self.capacity = 10
        self.attached_objects = []
        self.position = [0,0]
        self.signals = []

        self.dead = False
        self.moveable = True

    def step(self):
        """Represent a single step of the agent."""
        pass

    def advance(self):
        """Actions to do after a step of the agent."""
        pass

    def get_capacity(self):
        """Compute the remaining capacity of the agent.

        The capacity of the agent is fixed. Based on the objects it is
        carrying we need to adjust/reflect on the capacity of the agent.
        """
        relative_capacity = self.capacity
        for item in self.attached_objects:
            try:
                relative_capacity -= item.capacity
            except KeyError:
                self.attached_objects.remove(item)

        if relative_capacity < 0:
            return 0
        else:
            return relative_capacity

class TestAgent(Agent):
    def __init__(self, name, runtime):
        super().__init__(name, runtime)
