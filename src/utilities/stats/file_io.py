from copy import copy
from os import getcwd, makedirs, path
from shutil import rmtree

#from algorithm.parameters import params
from utilities.stats import trackers


def save_stats_to_file(stats, end=False):
    """
    Write the results to a results file for later analysis

    :param stats: The stats.stats.stats dictionary.
    :param end: A boolean flag indicating whether or not the evolutionary
    process has finished.
    :return: Nothing.
    """

    if params['VERBOSE']:
        filename = path.join(params['FILE_PATH'], "stats.tsv")
        savefile = open(filename, 'a')
        for stat in sorted(stats.keys()):
            savefile.write(str(stats[stat]) + "\t")
        savefile.write("\n")
        savefile.close()

    elif end:
        filename = path.join(params['FILE_PATH'], "stats.tsv")
        savefile = open(filename, 'a')
        for item in trackers.stats_list:
            for stat in sorted(item.keys()):
                savefile.write(str(item[stat]) + "\t")
            savefile.write("\n")
        savefile.close()


def save_stats_headers(stats):
    """
    Saves the headers for all stats in the stats dictionary.

    :param stats: The stats.stats.stats dictionary.
    :return: Nothing.
    """

    filename = path.join(params['FILE_PATH'], "stats.tsv")
    savefile = open(filename, 'w')
    for stat in sorted(stats.keys()):
        savefile.write(str(stat) + "\t")
    savefile.write("\n")
    savefile.close()


def save_best_ind_to_file(stats, ind, end=False, name="best"):
    """
    Saves the best individual to a file.

    :param stats: The stats.stats.stats dictionary.
    :param ind: The individual to be saved to file.
    :param end: A boolean flag indicating whether or not the evolutionary
    process has finished.
    :param name: The name of the individual. Default set to "best".
    :return: Nothing.
    """

    filename = path.join(params['FILE_PATH'], (str(name) + ".txt"))
    savefile = open(filename, 'w')
    savefile.write("Generation:\n" + str(stats['gen']) + "\n\n")
    savefile.write("Phenotype:\n" + str(ind.phenotype) + "\n\n")
    savefile.write("Genotype:\n" + str(ind.genome) + "\n")
    savefile.write("Tree:\n" + str(ind.code_tree) + "\n")
    if hasattr(params['FITNESS_FUNCTION'], "training_test"):
        if end:
            savefile.write("\nTraining fitness:\n" + str(ind.training_fitness))
            savefile.write("\nTest fitness:\n" + str(ind.test_fitness))
        else:
            savefile.write("\nFitness:\n" + str(ind.fitness))
    else:
        savefile.write("\nFitness:\n" + str(ind.fitness))
    savefile.close()


def save_first_front_to_file(stats, end=False, name="first", agent=None):
    """
    Saves all individuals in the first front to individual files in a folder.

    :param stats: The stats.stats.stats dictionary.
    :param end: A boolean flag indicating whether or not the evolutionary
                process has finished.
    :param name: The name of the front folder. Default set to "first_front".
    :return: Nothing.
    """

    # Save the file path (we will be over-writing it).
    orig_file_path = copy(agent.GE_params['FILE_PATH'])

    # Define the new file path.
    agent.GE_params['FILE_PATH'] = path.join(orig_file_path, str(name) + "_front")

    # Check if the front folder exists already
    if path.exists(agent.GE_params['FILE_PATH']):
        # Remove previous files.
        rmtree(agent.GE_params['FILE_PATH'])

    # Create front folder.
    makedirs(agent.GE_params['FILE_PATH'])

    for i, ind in enumerate(trackers.best_ever):
        # Save each individual in the first front to file.
        save_best_ind_to_file(stats, ind, end, name=str(i))

    # Re-set the file path.
    agent.GE_params['FILE_PATH'] = copy(orig_file_path)


def generate_folders_and_files(agent=None):
    """
    Generates necessary folders and files for saving statistics and parameters.

    :return: Nothing.
    """

    if agent.GE_params['EXPERIMENT_NAME']:
        # Experiment manager is being used.
        path_1 = path.join(getcwd(), "..", "results")

        if not path.isdir(path_1):
            # Create results folder.
            makedirs(path_1, exist_ok=True)

        # Set file path to include experiment name.
        agent.GE_params['FILE_PATH'] = path.join(path_1, agent.GE_params['EXPERIMENT_NAME'])

    else:
        # Set file path to results folder.
        agent.GE_params['FILE_PATH'] = path.join(getcwd(), "..", "results")

    # Generate save folders
    if not path.isdir(agent.GE_params['FILE_PATH']):
        makedirs(agent.GE_params['FILE_PATH'], exist_ok=True)

    if not path.isdir(path.join(agent.GE_params['FILE_PATH'],
                                str(agent.GE_params['LOG_FOLDER']))):
        makedirs(path.join(agent.GE_params['FILE_PATH'],
                           str(agent.GE_params['LOG_FOLDER'])), exist_ok=True)

    agent.GE_params['FILE_PATH'] = path.join(agent.GE_params['FILE_PATH'],
                                    str(agent.GE_params['LOG_FOLDER']))

    save_params_to_file(agent=agent)


def save_params_to_file(agent=None):
    """
    Save evolutionary parameters in a parameters.txt file.

    :return: Nothing.
    """

    # Generate file path and name.
    filename = path.join(agent.GE_params['FILE_PATH'], "parameters.txt")
    savefile = open(filename, 'w')

    # Justify whitespaces for pretty printing/saving.
    col_width = max(len(param) for param in agent.GE_params.keys())

    for param in sorted(agent.GE_params.keys()):
        # Create whitespace buffer for pretty printing/saving.
        spaces = [" " for _ in range(col_width - len(param))]
        savefile.write(str(param) + ": " + "".join(spaces) +
                       str(agent.GE_params[param]) + "\n")

    savefile.close()
