#from algorithm.parameters import params
from src.stats.stats import stats


def clean_stats(agent=None):
    """
    Removes certain unnecessary stats from the stats.stats.stats dictionary
    to clean up the current run.
    
    :return: Nothing.
    """

    if not agent.GE_params['CACHE']:
        try:
            stats.pop('unique_inds')
        except KeyError:
            pass

        try:
            stats.pop('unused_search')
        except KeyError:
            pass

    if not agent.GE_params['MUTATE_DUPLICATES']:
        try:
            stats.pop('regens')
        except KeyError:
            pass
