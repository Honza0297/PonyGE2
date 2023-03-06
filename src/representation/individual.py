import numpy as np

from algorithm.mapper import mapper
from algorithm.parameters import params
from re import finditer, match


class CodeTree(object):
    def __init__(self, tree, parent=None, lhs=None):
        self.valid = True
        self.tree = tree
        self.lhs = lhs
        self.rhs = list()
        self.children = list()
        self.raw_code = None
        self.code = list()
        self.parent = parent
        self.aliases = {}
        self.symbol_table = {}
        if not self.parent:
            self.make_symbol_table()
        else:
            self.symbol_table = self.parent.symbol_table

    def build(self):
        if not self.lhs:
            self.lhs = NonTerminal(self.tree.root, self.symbol_table[self.tree.root])
        self.rhs = [NonTerminal(node.root, self.symbol_table[node.root]) if node.root in self.symbol_table.keys() else Terminal(node.root) for node in self.tree.children]
        self.set_aliases()
        for tree_child, rhs_child in zip(self.tree.children, self.rhs):
            self.children.append(CodeTree(tree_child, self, rhs_child))
        self.parse_code(self.tree.raw_code)
        for child in self.children:
            child.build()

    def __str__(self):
        return str(self.lhs) + " -> " + str(self.rhs)

    def parse_code(self, raw_code):
        self.raw_code = raw_code
        if not self.raw_code:
            return
        template = "self.aliases[\"{}\"].attributes[\"{}\"][\"value\"]"
        for line in self.raw_code.splitlines():
            line = line.strip()
            if not line:
                continue
            nt_and_attr_regex = '\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|\"(.*?)\"|(?P<subrule><[^>|\s]+>\.[A-Za-z1-9_]+)|([<]+)'
            tmp_line = list()
            for ntas in finditer(nt_and_attr_regex, line):
                # noinspection DuplicatedCode
                if not ntas.group("subrule"):
                    if ntas.group(0).strip():  # ntas is not empty
                        tmp_ntas = ntas.group(0).strip()
                        if "ok()" in ntas.group(0):
                            tmp_ntas = tmp_ntas.replace("ok()", "self.ok()")
                        if "error()" in ntas.group(0):
                            tmp_ntas = tmp_ntas.replace("error()", "self.error()")
                        tmp_line.append(tmp_ntas)
                elif ntas.group("subrule"):
                    nt, attr = ntas.group("subrule").split(".")
                    tmp_line.append(template.format(nt, attr))
            self.code.append(tmp_line)

    def get_child(self, nonterm):
        for c in self.tree.children:
            if c.root == nonterm:
                return c
        return None

    def set_aliases(self):
        if not self.tree.raw_code:
            return
            # Set proper aliases
            # for example: in rule <S> ::= <S><A> we need to distinguish between first and second <S>
            # in attribute code, it is done by giving them and index: <S_1>, <S_2> etc., while <A> wont be changed
            # aliases thus are:
            # <S>   <S>   <A>
            # <S_1> <S_2> <A>
        nts_in_rule = [self.lhs.name] + [token.name if isinstance(token, NonTerminal) else None for token in self.rhs]
        while None in nts_in_rule:
            nts_in_rule.remove(None)

        counts = dict()
        aliases = list()
        for nt in nts_in_rule:
            counts[nt] = nts_in_rule.count(nt)
        for nt in nts_in_rule:
            if nts_in_rule.count(nt) == 1:
                aliases.append(nt)
            else:
                aliases.append(
                    "<" + nt[1:-1] + "_" + str(nts_in_rule.count(nt) - counts[nt] + 1) + ">")
                counts[nt] -= 1

        nonterminals = [self.lhs] + [token if isinstance(token, NonTerminal) else None for token in self.rhs]
        while None in nonterminals:
            nonterminals.remove(None)
        for i in range(len(nonterminals)):
            self.aliases[aliases[i]] = nonterminals[i]

    def make_symbol_table(self):
        tmp = params["BNF_GRAMMAR"].non_terminals
        nts = dict()
        filename = "../grammars/"+params["GRAMMAR_FILE"] + ".symbols"
        with open(filename, "r") as f:
            blocks = f.read().split("---")
            for block in blocks:
                block = block.strip()
                block = block.splitlines()
                if not block:
                    continue
                self.symbol_table[block[0]] = {}
                for line in block[1:]:
                    line = line.strip()
                    if not line:
                        continue

                    name, attribute_type, default_value = line.split(",")
                    self.symbol_table[block[0]][name] = {"type": attribute_type.strip(), "value": default_value.strip()}
        print(self.symbol_table)

    def run(self):
        ntas_regex = "self\.aliases\[\"\<[a-zA-Z1-9_]+\>\"\]\.attributes\[\"[a-z_1-9]+\"\]\[\"value\"\]"
        run_children = False
        children_ran = False
        for code_line in self.code:
            # dummy = "".join(code_line)
            nt, var = None, None

            # First part in the code line is a non-terminal -> this line is and assignment
            if match(ntas_regex, code_line[0]):
                nt, var = self._get_nt_and_var_from_code_line_part(code_line[0])
            else:
                for item in code_line:
                    if match(ntas_regex, item):
                        nt, var = self._get_nt_and_var_from_code_line_part(item)
            attribute_type = self.aliases[nt].attributes[var]["type"]
            if attribute_type == "I":
                try:
                    exec(" ".join(code_line))
                    run_children = True
                except Exception as e:
                    print(" ".join(code_line))
                    print(e)
            elif attribute_type == "S":
                operators = ["+=", "-=", "/=", "*=", "<", ">", ">=", "<="]
                # check whether it is a literal assignment - in that case, treat it like "I" type
                # in case if literal assignment, the = and literal are parsed as one token -> check length should be ok
                if len(code_line[1].strip()) > 1 or code_line[1].strip() in operators:
                    try:
                        exec(" ".join(code_line))
                        run_children = True
                    except Exception as e:
                        print(" ".join(code_line))
                        print(e)
                else:
                    if not children_ran:
                        children_ran = True
                        for child in self.children:
                            # Check for leafs and perform recursive code run only if it will
                            # be applied to non-leaf
                            if child.lhs.name in self.symbol_table.keys():
                                child.run()
                    try:
                        exec(" ".join(code_line))
                    except Exception as e:
                        print(" ".join(code_line))
                        print(e)

        if run_children and not children_ran:
            for child in self.children:
                if child.lhs.name in self.symbol_table.keys():
                    child.run()

        if not self.parent:
            self.check_validity()

    def check_validity(self):
        if not self.parent: # root
            if not self.children: # trunk
                return
            else: # standard root
                self.valid = min([self.valid] + [child.check_validity() for child in self.children])
        else: # node/leaf
            if not self.children: # leaf
                return self.valid
            else:
                return min([self.valid] + [child.check_validity() for child in self.children])

    def error(self):
        self.valid = False
        print("EEEERRRROOOORRRR")

    def ok(self):
        print("OOOKKK")

    def _get_nt_and_var_from_code_line_part(self, text):
        nt = "<" + text.split("<")[1].split(">")[0] + ">"
        var = None
        var_id_regex = r'(?P<var_id>(?<=\.attributes\[\")[a-z\_1-9]+)'
        for regex_match in finditer(var_id_regex, text):
            if regex_match.group("var_id"):
                var = regex_match.group("var_id")
                return nt, var


class Terminal(object):
    def __init__(self, name=""):
        self.name = name


class NonTerminal(object):
    def __init__(self, name="", attributes=None):
        self.name = name
        self.attributes = {}
        if not attributes and name in params["BNF_GRAMMAR"].non_terminals.keys():
            for attr in params["BNF_GRAMMAR"].non_terminals[name]["attributes"].keys():
                self.attributes[attr] = {"type": None, "value": None}
        else:
            for attribute in attributes: # need to make a copy
                self.attributes[attribute] = {"type": None, "value": None}
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
        self.code_tree.build()

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
