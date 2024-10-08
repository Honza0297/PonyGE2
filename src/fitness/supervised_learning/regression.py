#from algorithm.parameters import params
from fitness.supervised_learning.supervised_learning import supervised_learning
from utilities.fitness.error_metric import rmse


class regression(supervised_learning):
    """Fitness function for regression. We just slightly specialise the
    function for supervised_learning."""

    def __init__(self, agent=None):
        # Initialise base fitness function class.
        super().__init__(agent)

        # Set error metric if it's not set already.
        if agent.GE_params['ERROR_METRIC'] is None:
            agent.GE_params['ERROR_METRIC'] = rmse

        self.maximise = agent.GE_params['ERROR_METRIC'].maximise
