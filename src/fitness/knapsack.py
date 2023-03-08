from fitness.base_ff_classes.base_ff import base_ff


class knapsack(base_ff):
    maximise = True

    def __init__(self):
        # Initialise base fitness function class.
        super().__init__()

    def evaluate(self, ind, **kwargs):

        capacity = 21

        weights = {'i1': 8, 'i2': 9, 'i3': 4, 'i4': 10, 'i5': 4, 'i6': 3, 'i7': 6, 'i8': 2, 'i9': 6}
        values = {'i1': 7, 'i2': 2, 'i3': 5, 'i4': 8, 'i5': 7, 'i6': 4, 'i7': 4, 'i8': 6, 'i9': 10}

        if ind.invalid:
            return self.default_fitness

        tmp_fitness = self.default_fitness

        item_list = ["i"+i for i in ind.phenotype.split("i")[1:]]
        weight = 0
        value = 0
        for i in item_list:
            if item_list.count(i) > 1: # items repeated
                tmp_fitness = self.default_fitness
                break
            weight += weights[i]
            value += values[i]

        if weight <= capacity:
            tmp_fitness = weight/capacity*value

        return tmp_fitness
