from collections import deque

import numpy as np
#from algorithm.parameters import params
from representation.tree import Tree
from utilities.representation.python_filter import python_filter


def mapper(genome, tree, agent=None):
    """
    Wheel for mapping. Calls the correct mapper for a given _input. Checks
    the params dict to ensure the correct type of individual is being created.

    If a genome is passed in with no tree, all tree-related information is
    generated. If a tree is passed in with no genome, the genome is
    sequenced from the tree.

    :param genome: Genome of an individual.
    :param tree: Tree of an individual.
    :return: All components necessary for a fully mapped individual.
    """

    # one or other must be passed in, but not both
    assert (genome or tree)
    assert not (genome and tree)

    if genome:
        # We have a genome and need to map an individual from that genome.

        genome = list(genome)
        # This is a fast way of creating a new unique copy of the genome
        # (prevents cross-contamination of information between individuals).

        if agent.GE_params['GENOME_OPERATIONS']:
            # Can generate tree information faster using
            # algorithm.mapper.map_ind_from_genome() if we don't need to
            # store the whole tree.
            phenotype, genome, tree, nodes, invalid, depth, \
            used_codons = map_ind_from_genome(genome, agent=agent)

        else:
            # Build the tree using algorithm.mapper.map_tree_from_genome().
            phenotype, genome, tree, nodes, invalid, depth, \
            used_codons = map_tree_from_genome(genome)

    else:
        # We have a tree.

        # genome, output, invalid, depth, and nodes can all be
        # generated by recursing through the tree once.

        genome, output, invalid, depth, \
        nodes = tree.get_tree_info(agent.GE_params['BNF_GRAMMAR'].non_terminals.keys(),
                                   [], [])
        used_codons, phenotype = len(genome), "".join(output)

    if agent.GE_params['BNF_GRAMMAR'].python_mode and not invalid:
        # Grammar contains python code

        phenotype = python_filter(phenotype)

    if invalid:
        # Set values for invalid individuals.
        phenotype, nodes, depth, used_codons = None, np.NaN, np.NaN, np.NaN

    return phenotype, genome, tree, nodes, invalid, depth, used_codons


def map_ind_from_genome(genome, agent=None):
    """
    A fast genotype to phenotype mapping process. Map input via rules to
    output. Does not require the recursive tree class, but still calculates
    tree information, e.g. number of nodes and maximum depth.

    :param genome: A genome to be mapped.
    :return: Output in the form of a phenotype string ('None' if invalid),
             Genome,
             None (this is reserved for the derivation tree),
             The number of nodes in the derivation,
             A boolean flag for whether or not the individual is invalid,
             The maximum depth of any node in the tree, and
             The number of used codons.
    """

    # Create local variables to avoid multiple dictionary lookups
    max_tree_depth, max_wraps = agent.GE_params['MAX_TREE_DEPTH'], agent.GE_params['MAX_WRAPS']
    bnf_grammar = agent.GE_params['BNF_GRAMMAR']

    n_input = len(genome)

    # Depth, max_depth, and nodes start from 1 to account for starting root
    # Initialise number of wraps at -1 (since
    used_input, current_depth, max_depth, nodes, wraps = 0, 1, 1, 1, -1

    # Initialise output as empty deque list (deque is a list-like container
    # with fast appends and pops on either end).
    output = deque()

    # Initialise the list of unexpanded non-terminals with the start rule.
    unexpanded_symbols = deque([(bnf_grammar.start_rule, 1)])

    while (wraps < max_wraps) and unexpanded_symbols:
        # While there are unexpanded non-terminals, and we are below our
        # wrapping limit, we can continue to map the genome.

        if max_tree_depth and (max_depth > max_tree_depth):
            # We have breached our maximum tree depth limit.
            break

        if used_input % n_input == 0 and \
                used_input > 0 and \
                any([i[0]["type"] == "NT" for i in unexpanded_symbols]):
            # If we have reached the end of the genome and unexpanded
            # non-terminals remain, then we need to wrap back to the start
            # of the genome again. Can break the while loop.
            wraps += 1

        # Expand a production from the list of unexpanded non-terminals.
        current_item = unexpanded_symbols.popleft()
        current_symbol, current_depth = current_item[0], current_item[1]

        if max_depth < current_depth:
            # Set the new maximum depth.
            max_depth = current_depth

        # Set output if it is a terminal.
        if current_symbol["type"] != "NT":
            output.append(current_symbol["symbol"])

        else:
            # Current item is a new non-terminal. Find associated production
            # choices.
            production_choices = bnf_grammar.rules[current_symbol[
                "symbol"]]["choices"]
            no_choices = bnf_grammar.rules[current_symbol["symbol"]][
                "no_choices"]

            # Select a production based on the next available codon in the
            # genome.
            current_production = genome[used_input % n_input] % no_choices

            # Use an input
            used_input += 1

            # Initialise children as empty deque list.
            children = deque()
            nt_count = 0

            for prod in production_choices[current_production]['choice']:
                # iterate over all elements of chosen production rule.

                child = [prod, current_depth + 1]

                # Extendleft reverses the order, thus reverse adding.
                children.appendleft(child)
                if child[0]["type"] == "NT":
                    nt_count += 1

            # Add the new children to the list of unexpanded symbols.
            unexpanded_symbols.extendleft(children)

            if nt_count > 0:
                nodes += nt_count
            else:
                nodes += 1

    # Generate phenotype string.
    output = "".join(output)

    if len(unexpanded_symbols) > 0:
        # All non-terminals have not been completely expanded, invalid
        # solution.
        return None, genome, None, nodes, True, max_depth, used_input

    return output, genome, None, nodes, False, max_depth, used_input


def map_tree_from_genome(genome):
    """
    Maps a full tree from a given genome.

    :param genome: A genome to be mapped.
    :return: All components necessary for a fully mapped individual.
    """

    # Initialise an instance of the tree class
    tree = Tree(str(agent.GE_params['BNF_GRAMMAR'].start_rule["symbol"]), None)

    # Map tree from the given genome
    output, used_codons, nodes, depth, max_depth, invalid = \
        genome_tree_map(tree, genome, [], 0, 0, 0, 0)

    # Build phenotype.
    phenotype = "".join(output)

    if invalid:
        # Return "None" phenotype if invalid
        return None, genome, tree, nodes, invalid, max_depth, \
               used_codons

    else:
        return phenotype, genome, tree, nodes, invalid, max_depth, \
               used_codons


def genome_tree_map(tree, genome, output, index, depth, max_depth, nodes,
                    invalid=False, agent=None):
    """
    Recursive function which builds a tree using production choices from a
    given genome. Not guaranteed to terminate.

    :param tree: An instance of the representation.tree.Tree class.
    :param genome: A full genome.
    :param output: The list of all terminal nodes in a subtree. This is
    joined to become the phenotype.
    :param index: The index of the current location on the genome.
    :param depth: The current depth in the tree.
    :param max_depth: The maximum overall depth in the tree so far.
    :param nodes: The total number of nodes in the tree thus far.
    :param invalid: A boolean flag indicating whether or not the individual
    is invalid.
    :return: index, the index of the current location on the genome,
             nodes, the total number of nodes in the tree thus far,
             depth, the current depth in the tree,
             max_depth, the maximum overall depth in the tree,
             invalid, a boolean flag indicating whether or not the
             individual is invalid.
    """

    if not invalid and index < len(genome) * (agent.GE_params['MAX_WRAPS'] + 1):
        # If the solution is not invalid thus far, and if we still have
        # remaining codons in the genome, then we can continue to map the tree.

        if agent.GE_params['MAX_TREE_DEPTH'] and (max_depth > agent.GE_params['MAX_TREE_DEPTH']):
            # We have breached our maximum tree depth limit.
            invalid = True

        # Increment and set number of nodes and current depth.
        nodes += 1
        depth += 1
        tree.id, tree.depth = nodes, depth

        # Find all production choices and the number of those production
        # choices that can be made by the current root non-terminal.
        productions = agent.GE_params['BNF_GRAMMAR'].rules[tree.root]['choices']
        no_choices = agent.GE_params['BNF_GRAMMAR'].rules[tree.root]['no_choices']

        # Set the current codon value from the genome.
        tree.codon = genome[index % len(genome)]

        # Select the index of the correct production from the list.
        selection = tree.codon % no_choices

        # Set the chosen production
        chosen_prod = productions[selection]

        # Increment the index
        index += 1

        # Initialise an empty list of children.
        tree.children = []
        # copy attribute code if attribute grammar is used
        if agent.GE_params["ATTRIBUTE_GRAMMAR"]:
            tree.attr_code.set_attr_code(chosen_prod["attr_code"])
            tree.raw_code = chosen_prod["attr_code"][1:-1]

        for symbol in chosen_prod['choice']:
            # Add children to the derivation tree by creating a new instance
            # of the representation.tree.Tree class for each child.

            if symbol["type"] == "T":
                # Append the child to the parent node. Child is a terminal, do
                # not recurse.
                tree.children.append(Tree(symbol["symbol"], tree))
                output.append(symbol["symbol"])

            elif symbol["type"] == "NT":
                # Append the child to the parent node.
                tree.children.append(Tree(symbol["symbol"], tree))

                # Recurse by calling the function again to map the next
                # non-terminal from the genome.
                output, index, nodes, d, max_depth, invalid = \
                    genome_tree_map(tree.children[-1], genome, output,
                                    index, depth, max_depth, nodes,
                                    invalid=invalid)

    else:
        # Mapping incomplete, solution is invalid.
        return output, index, nodes, depth, max_depth, True

    # Find all non-terminals in the chosen production choice.
    NT_kids = [kid for kid in tree.children if kid.root in
               agent.GE_params['BNF_GRAMMAR'].non_terminals]

    if not NT_kids:
        # There are no non-terminals in the chosen production choice, the
        # branch terminates here.
        depth += 1
        nodes += 1

    if not invalid:
        # The solution is valid thus far.

        if depth > max_depth:
            # Set the new maximum depth.
            max_depth = depth

        if agent.GE_params['MAX_TREE_DEPTH'] and (max_depth > agent.GE_params['MAX_TREE_DEPTH']):
            # If our maximum depth exceeds the limit, the solution is invalid.
            invalid = True

    return output, index, nodes, depth, max_depth, invalid
