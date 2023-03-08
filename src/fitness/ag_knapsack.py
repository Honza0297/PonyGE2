from fitness.base_ff_classes.base_ff import base_ff


class ag_knapsack(base_ff):

    maximise = True

    def __init__(self):
        """
        All fitness functions which inherit from the bass fitness function
        class must initialise the base class during their own initialisation.
        """

        # Initialise base fitness function class.
        super().__init__()

    def evaluate(self, ind, **kwargs):

        # Evaluate the fitness of the phenotype
        if ind.invalid:
            return self.default_fitness
        if not ind.code_tree:
            print("FAIL")

        capacity = -1
        try:
            capacity = ind.code_tree.aliases["<K>"].attributes["c"]["value"]
        except Exception as e:
            print("WTF")

        weight = ind.code_tree.aliases["<K>"].attributes["w"]["value"]
        value = ind.code_tree.aliases["<K>"].attributes["v"]["value"]
        fitness = weight/capacity*value

        return fitness
