import numpy as np

from algorithm.mapper import mapper
from algorithm.parameters import params
from re import finditer


class CodeTree(object):
    def __init__(self, tree, parent=None, lhs=None):
        self.lhs = lhs
        self.rhs = list()
        self.children = list()
        self.raw_code = None
        self.code = None
        self.parent = parent
        self.aliases = {}
        if not self.parent:
            self.make_symbol_table(tree)
        else:
            self.symbol_table = self.parent.symbol_table

        self.build(tree)

    def build(self, tree):
        if not self.lhs:
            self.lhs = NonTerminal(tree.root, self.symbol_table[tree.root])
        self.rhs = [NonTerminal(node.root, self.symbol_table[tree.root]) for node in tree.children]
        self.set_aliases(tree)
        self.parse_code(tree)
        self.children = [CodeTree(tree.children[i], self, self.rhs[i]) for i in range(len(tree.children))]

    def __str__(self):
        return str(self.lhs) + " -> " + str(self.rhs)

    def parse_code(self, tree):
        for line in tree.raw_code.splitlines():
            line = line.strip()
            if not line:
                continue

            # returns string in a form of NT.attr_name (<A>.val, <S_1>.itemcount_3 etc.).
            # Only alphanumeric characters and underscore (_) are allowed in the attribute name
            nt_and_attr_regex = '\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|"(.*?)"|(?P<subrule><[^>|\s]+>\.[A-Za-z1-9_]+)|([<]+)'

            first = True
            for ntas in finditer(nt_and_attr_regex, line):
                if not ntas.group("subrule"):
                    continue
                nt, attr = ntas.group("subrule").split(".")
                # if the first processed attribute seems to belong to the lhs of current rule, suppose it is synthesized
                if self.aliases[nt] == self.lhs and first and self.aliases[nt].attributes[attr]["type"] is None:
                    self.aliases[nt].attributes[attr]["type"] = "S"  # attribute is syntesized
                # else if it is not current lhs, this attribute is probably inherited
                elif self.aliases[nt] != self.lhs and first and self.aliases[nt].attributes[attr]["type"] is None:
                    self.aliases[nt].attributes[attr]["type"] = "I"
                first = False
                if not first:
                    break

    def get_child(self, nonterm, tree):
        for c in tree.children:
            if c.root == nonterm:
                return c
        return None

    def set_aliases(self, tree):
        if not tree.raw_code:
            return
            # Set proper aliases
            # for example: in rule <S> ::= <S><A> we need to distinguish between first and second <S>
            # in attribute code, it is done by giving them and index: <S_1>, <S_2> etc., while <A> wont be changed
            # aliases thus are:
            # <S>   <S>   <A>
            # <S_1> <S_2> <A>
        nts_in_rule = [tree.root] + [child.root for child in tree.children]
        counts = list()
        aliases = list()
        for nt in nts_in_rule:
            counts.append(nts_in_rule.count(nt))
        for i in range(len(nts_in_rule)):
            if nts_in_rule.count(nts_in_rule[i]) == 1:
                aliases.append(nts_in_rule[i])
            else:
                aliases.append(
                    "<" + nts_in_rule[i][1:-1] + "_" + str(nts_in_rule.count(nts_in_rule[i]) - counts[i] + 1) + ">")
                counts[i] -= 1

        nonterminals = [self.lhs] + self.rhs
        for i in range(len(nonterminals)):
            self.aliases[aliases[i]] = nonterminals[i]

    def make_symbol_table(self, tree):
        tmp = params["BNF_GRAMMAR"].non_terminals
        nts = dict()
        for nt in tmp.keys():
            nts[nt] = tmp[nt]["attributes"]
        # todo zjistit typy atributů

        self.symbol_table = nts
class NonTerminal(object):
    def __init__(self, name="", attributes=None):
        self.name = name
        self.attributes = {}
        if attributes is None and name in params["BNF_GRAMMAR"].non_terminals.keys():
            for attr in params["BNF_GRAMMAR"].non_terminals[name]["attributes"].keys():
                self.attributes[attr] = {"type": None, "value": None}
        else:
            self.attributes = attributes

    def __str__(self):
        return str(self.name) + ": " + str(self.attributes)


class Individual(object):
    """
    A GE individual.
    """

    def __init__(self, genome, ind_tree, map_ind=True):
        """
        Initialise an instance of the individual class (i.e. create a new
        individual).

        :param genome: An individual's genome.
        :param ind_tree: An individual's derivation tree, i.e. an instance
        of the representation.tree.Tree class.
        :param map_ind: A boolean flag that indicates whether or not an
        individual needs to be mapped.
        """

        if map_ind:
            # The individual needs to be mapped from the given input
            # parameters.
            self.phenotype, self.genome, self.tree, self.nodes, self.invalid, \
                self.depth, self.used_codons = mapper(genome, ind_tree)

        else:
            # The individual does not need to be mapped.
            self.genome, self.tree = genome, ind_tree

        self.fitness = params['FITNESS_FUNCTION'].default_fitness
        self.runtime_error = False
        self.name = None
        if params["ATTRIBUTE_GRAMMAR"]:
            self.code_tree = None

    def __lt__(self, other):
        """
        Set the definition for comparison of two instances of the individual
        class by their fitness values. Allows for sorting/ordering of a
        population of individuals. Note that numpy NaN is used for invalid
        individuals and is used by some fitness functions as a default fitness.
        We implement a custom catch for these NaN values.

        :param other: Another instance of the individual class (i.e. another
        individual) with which to compare.
        :return: Whether or not the fitness of the current individual is
        greater than the comparison individual.
        """

        if np.isnan(self.fitness):
            return True
        elif np.isnan(other.fitness):
            return False
        else:
            return self.fitness < other.fitness if params[
                'FITNESS_FUNCTION'].maximise else other.fitness < self.fitness

    def __le__(self, other):
        """
        Set the definition for comparison of two instances of the individual
        class by their fitness values. Allows for sorting/ordering of a
        population of individuals. Note that numpy NaN is used for invalid
        individuals and is used by some fitness functions as a default fitness.
        We implement a custom catch for these NaN values.

        :param other: Another instance of the individual class (i.e. another
        individual) with which to compare.
        :return: Whether or not the fitness of the current individual is
        greater than or equal to the comparison individual.
        """

        if np.isnan(self.fitness):
            return True
        elif np.isnan(other.fitness):
            return False
        else:
            return self.fitness <= other.fitness if params[
                'FITNESS_FUNCTION'].maximise else other.fitness <= self.fitness

    def __str__(self):
        """
        Generates a string by which individuals can be identified. Useful
        for printing information about individuals.

        :return: A string describing the individual.
        """
        return ("Individual: " +
                str(self.phenotype) + "; " + str(self.fitness))

    def make_code_tree(self):
        self.code_tree = CodeTree(tree=self.tree, parent=None, lhs={})
        #self.code_tree.build(self.tree)

    def deep_copy(self):
        """
        Copy an individual and return a unique version of that individual.

        :return: A unique copy of the individual.
        """

        if not params['GENOME_OPERATIONS']:
            # Create a new unique copy of the tree.
            new_tree = self.tree.__copy__()

        else:
            new_tree = None

        # Create a copy of self by initialising a new individual.
        new_ind = Individual(self.genome.copy(), new_tree, map_ind=False)

        # Set new individual parameters (no need to map genome to new
        # individual).
        new_ind.phenotype, new_ind.invalid = self.phenotype, self.invalid
        new_ind.depth, new_ind.nodes = self.depth, self.nodes
        new_ind.used_codons = self.used_codons
        new_ind.runtime_error = self.runtime_error

        return new_ind

    def evaluate(self):
        """
        Evaluates phenotype in using the fitness function set in the params
        dictionary. For regression/classification problems, allows for
        evaluation on either training or test distributions. Sets fitness
        value.

        :return: Nothing unless multi-core evaluation is being used. In that
        case, returns self.
        """

        # Evaluate fitness using specified fitness function.
        self.fitness = params['FITNESS_FUNCTION'](self)

        if params['MULTICORE']:
            return self
