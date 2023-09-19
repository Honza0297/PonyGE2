import math

from src.fitness.base_ff_classes.base_ff import base_ff
import random
import xml.etree.ElementTree as ET

class swarm_fitness_diversity(base_ff):

    maximise = True

    def __init__(self):
        """
        All fitness functions which inherit from the bass fitness function
        class must initialise the base class during their own initialisation.
        """

        # Initialise base fitness function class.
        super().__init__()
        # Simplified in comparison to Aadesh
        self.execution_behaviors = ["GoTo", "NeighbourObjects", "CanCarry", "CanDrop", "IsCarrying", "PickUp", "Drop"]
        self.execution_behaviors.sort()

    def calcualte_diversity(self):
        self.sorted_keys = list(self.execution.keys())
        self.sorted_keys.sort()
        self.sorted_values = list(self.execution.values())
        self.sorted_values.sort()
        new_execution = dict()
        sorted_values_sum = sum(self.sorted_values)
        behavior_len = len(self.execution_behaviors)
        divisor = math.ceil(sorted_values_sum / behavior_len) * behavior_len
        if self.sorted_keys == self.execution_behaviors and \
                sorted_values_sum % behavior_len == 0 and \
                self.sorted_values[0] == int(
            sorted_values_sum / behavior_len):
            diversity = 1
        elif self.sorted_keys == self.execution_behaviors and \
                self.sorted_values[0] <= int(
            sorted_values_sum / behavior_len):
            for a in self.execution.keys():
                self.execution[a] -= self.sorted_values[0]
                if self.execution[a] > 0:
                    new_execution[a] = self.execution[a]
            other_match_count = self.other_match_value(new_execution)
            # diversity = (self.sorted_values[0] * behavior_len
            # + other_match_count * 1.0) / divisor
            diversity = 1.0 - (
                    other_match_count * self.sorted_values[-2] / 100.0)
        else:
            other_match_count = self.other_match_value(self.execution)
            diversity = (other_match_count * 1.0) / divisor

        return round(diversity * 25, 4)

    def other_match_value(self, execution):
        match_set = set(execution.keys()) & set(self.execution_behaviors)
        return len(match_set)

    def evaluate(self, ind, **kwargs):
        # Copied one to one from Aadesh
        ind.phenotype = ind.phenotype.replace('[', '<')
        ind.phenotype = ind.phenotype.replace(']', '>')
        ind.phenotype = ind.phenotype.replace('%', '"')
        self.root = ET.fromstring(ind.phenotype)
        self.control_behaviors = {'Selector', 'Sequence'}
        nodes = []
        self.control = dict()
        self.control['Sequence'] = 0
        self.control['Selector'] = 0
        self.execution = dict()
        for node in self.root.iter():
            if node.tag in ['Sequence', 'Selector']:
                self.control[node.tag] += 1
                nodes.append(node.tag)
            else:
                if node.text.find('_') != -1:
                    node_text = node.text.split('_')
                    node_text = node_text[0]
                else:
                    node_text = node.text
                try:
                    self.execution[node_text] += 1
                except KeyError:
                    self.execution[node_text] = 1
                nodes.append(node_text)
        fitness = self.calcualte_diversity()
        return fitness