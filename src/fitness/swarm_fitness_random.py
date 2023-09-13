from fitness.base_ff_classes.base_ff import base_ff
import random

class swarm_fitness_random(base_ff):

    maximise = True

    def __init__(self):
        """
        All fitness functions which inherit from the bass fitness function
        class must initialise the base class during their own initialisation.
        """

        # Initialise base fitness function class.
        super().__init__()

    def evaluate(self, ind, **kwargs):

        return random.randint(10,1000)
