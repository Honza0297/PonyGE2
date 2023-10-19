from multiprocessing import cpu_count
from os import path
from socket import gethostname

hostname = gethostname().split('.')
machine_name = hostname[0]

def load_params(file_name, agent=None):
    """
    Load in a params text file and set the params dictionary directly.

    :param file_name: The name/location of a parameters file.
    :return: Nothing.
    """
    try:
        open(file_name, "r")
    except FileNotFoundError:
        s = "algorithm.parameters.load_params\n" \
            "Error: Parameters file not found.\n" \
            "       Ensure file extension is specified, e.g. 'regression.txt'."
        raise Exception(s)

    with open(file_name, 'r') as parameters:
        # Read the whole parameters file.
        content = parameters.readlines()

        for line in [l for l in content if not l.startswith("#")]:

            # Parameters files are parsed by finding the first instance of a
            # colon.
            split = line.find(":")

            # Everything to the left of the colon is the parameter key,
            # everything to the right is the parameter value.
            key, value = line[:split], line[split + 1:].strip()

            # Evaluate parameters
            """try:
                value = eval(value)

            except:
                # We can't evaluate, leave value as a string.
                pass"""

            # Set parameter
            agent.GE_params[key] = value



def set_params(command_line_args, create_files=True, agent=None):
    """
    This function parses all command line arguments specified by the user.
    If certain parameters are not set then defaults are used (e.g. random
    seeds, elite size). Sets the correct imports given command line
    arguments. Sets correct grammar file and fitness function. Also
    initialises save folders and tracker lists in utilities.trackers.

    :param command_line_args: Command line arguments specified by the user.
    :return: Nothing.
    """

    from utilities.algorithm.initialise_run import initialise_run_params
    from utilities.algorithm.initialise_run import set_param_imports
    from utilities.fitness.math_functions import return_one_percent
    from utilities.algorithm.command_line_parser import parse_cmd_args
    from utilities.stats import trackers, clean_stats
    from representation import grammar

    cmd_args, unknown = parse_cmd_args(command_line_args)

    if unknown:
        # We currently do not parse unknown parameters. Raise error.
        s = "algorithm.parameters.set_params\nError: " \
            "unknown parameters: %s\nYou may wish to check the spelling, " \
            "add code to recognise this parameter, or use " \
            "--extra_parameters" % str(unknown)
        raise Exception(s)

    # LOAD PARAMETERS FILE
    # NOTE that the parameters file overwrites all previously set parameters.
    if 'PARAMETERS' in cmd_args:
        load_params(path.join("..", "parameters", cmd_args['PARAMETERS']))

    # Join original params dictionary with command line specified arguments.
    # NOTE that command line arguments overwrite all previously set parameters.
    agent.GE_params.update(cmd_args)

    if agent.GE_params['LOAD_STATE']:  # NOTE: asi kdyz se nema zacinat od nuly?
        # Load run from state.
        from utilities.algorithm.state import load_state

        # Load in state information.
        individuals = load_state(agent.GE_params['LOAD_STATE'])

        # Set correct search loop.
        from algorithm.search_loop import search_loop_from_state
        agent.GE_params['SEARCH_LOOP'] = search_loop_from_state

        # Set population.
        setattr(trackers, "state_individuals", individuals)

    else:
        if agent.GE_params['REPLACEMENT'].split(".")[-1] == "steady_state":
            # Set steady state step and replacement.
            agent.GE_params['STEP'] = "steady_state_step"
            agent.GE_params['GENERATION_SIZE'] = 2

        else:
            # Elite size is set to either 1 or 1% of the population size,
            # whichever is bigger if no elite size is previously set.
            if agent.GE_params['ELITE_SIZE'] is None:
                agent.GE_params['ELITE_SIZE'] = return_one_percent(1, agent.GE_params[
                    'POPULATION_SIZE'])

            # Set the size of a generation
            agent.GE_params['GENERATION_SIZE'] = int(agent.GE_params['POPULATION_SIZE']) - \
                                        int(agent.GE_params['ELITE_SIZE'])

        if (agent.GE_params['MUTATION_PROBABILITY'] is not None and
            agent.GE_params['MUTATION_EVENTS'] != 1):
            s = "operators.mutation.int_flip_per_codon\n" \
                "Error: mutually exclusive parameters 'MUTATION_PROBABILITY'" \
                "and 'MUTATION_EVENTS' have been explicitly set.\n" \
                "Only one of these parameters can be used at a time."
            raise Exception(s)

        # Initialise run lists and folders before we set imports.r
        initialise_run_params(create_files, agent=agent)

        # Set correct param imports for specified function options, including
        # error metrics and fitness functions.
        set_param_imports(agent=agent)

        # Clean the stats dict to remove unused stats.
        clean_stats.clean_stats(agent=agent)

        # Set GENOME_OPERATIONS automatically for faster linear operations.
        if (agent.GE_params['CROSSOVER'].representation == "subtree" or
                agent.GE_params['MUTATION'].representation == "subtree" or agent.GE_params["ATTRIBUTE_GRAMMAR"]):
            agent.GE_params['GENOME_OPERATIONS'] = False
        else:
            agent.GE_params['GENOME_OPERATIONS'] = True

        # Ensure correct operators are used if multiple fitness functions used.
        if hasattr(agent.GE_params['FITNESS_FUNCTION'], 'multi_objective'):

            # Check that multi-objective compatible selection is specified.
            if not hasattr(agent.GE_params['SELECTION'], "multi_objective"):
                s = "algorithm.parameters.set_params\n" \
                    "Error: multi-objective compatible selection " \
                    "operator not specified for use with multiple " \
                    "fitness functions."
                raise Exception(s)

            if not hasattr(agent.GE_params['REPLACEMENT'], "multi_objective"):

                # Check that multi-objective compatible replacement is
                # specified.
                if not hasattr(agent.GE_params['REPLACEMENT'], "multi_objective"):
                    s = "algorithm.parameters.set_params\n" \
                        "Error: multi-objective compatible replacement " \
                        "operator not specified for use with multiple " \
                        "fitness functions."
                    raise Exception(s)

        # Parse grammar file and set grammar class.
        agent.GE_params['BNF_GRAMMAR'] = grammar.Grammar(
                path.join("..", "grammars", agent.GE_params['GRAMMAR_FILE']), agent=agent)

        # If OPTIMIZE_CONSTANTS, check that the grammar is suitable
        if agent.GE_params['OPTIMIZE_CONSTANTS']:
            if "c[" not in agent.GE_params['BNF_GRAMMAR'].terminals:
                raise ValueError("Grammar unsuitable for OPTIMIZE_CONSTANTS")

        # Population loading for seeding runs (if specified)
        if agent.GE_params['TARGET_SEED_FOLDER']:

            # Import population loading function.
            from operators.initialisation import load_population

            # A target folder containing seed individuals has been given.
            agent.GE_params['SEED_INDIVIDUALS'] = load_population(
                agent.GE_params['TARGET_SEED_FOLDER'])

        elif agent.GE_params['REVERSE_MAPPING_TARGET']:
            # A single seed phenotype has been given. Parse and run.

            # Import GE LR Parser.
            from scripts import GE_LR_parser

            # Parse seed individual and store in params.
            agent.GE_params['SEED_INDIVIDUALS'] = [GE_LR_parser.main()]
