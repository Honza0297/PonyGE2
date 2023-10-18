import copy
from re import finditer, match


class CodeTree(object):
    def __init__(self, tree, parent=None, lhs=None, agent=None):
        self.agent = agent
        self.invalid = False
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
        self.rhs = [NonTerminal(node.root, self.symbol_table[node.root], agent=self.agent) if node.root in self.symbol_table.keys() else Terminal(node.root, agent=self.agent) for node in self.tree.children]
        self.set_aliases()
        for tree_child, rhs_child in zip(self.tree.children, self.rhs):
            self.children.append(CodeTree(tree_child, self, rhs_child, agent=self.agent))
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
        tmp = self.agent.GE_params["BNF_GRAMMAR"].non_terminals
        nts = dict()
        filename = "../grammars/"+self.agent.GE_params["GRAMMAR_FILE"] + ".symbols"
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
                    default_value = eval(default_value)
                    """types = [int, list, float]
                    for t in types:
                        try:
                            default_value = t(default_value)
                            break
                        except ValueError:
                            pass"""
                    self.symbol_table[block[0]][name] = {"type": attribute_type.strip(), "value": default_value.strip() if type(default_value) == str else default_value }
        #print(self.symbol_table)

    def run(self):
        ntas_regex = 'self\.aliases\[\"\<[a-zA-Z1-9_]+\>\"\]\.attributes\[\"[a-z_1-9]+\"\]\[\"value\"\]'
        run_children = False
        children_ran = False
        for code_line in self.code:
            # dummy = "".join(code_line)
            nt, var = None, None

            # First part in the code line is a non-terminal -> this line is an assignment
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
                    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAa")
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
                        print("\n\n"+str(repr(e))+"\n\n")
                        print("##########################################################################x")

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
                        print("SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSsss")

        if run_children and not children_ran:
            for child in self.children:
                if child.lhs.name in self.symbol_table.keys():
                    child.run()

        if not self.parent:
            self.check_validity()

    def check_validity(self):
        if not self.parent:  # root
            if not self.children:  # trunk
                return
            else:  # standard root
                self.invalid = any([self.invalid] + [child.check_validity() for child in self.children])
        else:  # node/leaf
            if not self.children:  # leaf
                return self.invalid
            else:
                return any([self.invalid] + [child.check_validity() for child in self.children])

    def error(self):
        self.invalid = False
        #print("EEEERRRROOOORRRR")

    def ok(self):
        # We do not set invalid flag here 'cause we would potentially overwrite some error
        pass
        #print("OOOKKK")

    def _get_nt_and_var_from_code_line_part(self, text):
        nt = "<" + text.split("<")[1].split(">")[0] + ">"
        var = None
        var_id_regex = r'(?P<var_id>(?<=\.attributes\[\")[a-z\_1-9]+)'
        for regex_match in finditer(var_id_regex, text):
            if regex_match.group("var_id"):
                var = regex_match.group("var_id")
                return nt, var

    def deep_copy(self):
        new_tree = self.tree.__copy__()
        new_code_tree = CodeTree(tree=new_tree, parent=self.parent, lhs=self.lhs, agent=self.agent)

        return new_code_tree


class Terminal(object):
    def __init__(self, name="", agent=None):
        self.agent = agent
        self.name = name


class NonTerminal(object):
    def __init__(self, name="", attributes=None, agent=None):
        self.agent = agent
        self.name = name
        self.attributes = {}
        if not attributes and name in self.agent.GE_params["BNF_GRAMMAR"].non_terminals.keys():
            for attr in self.agent.GE_params["BNF_GRAMMAR"].non_terminals[name]["attributes"].keys():
                self.attributes[attr] = {"type": None, "value": None}
        else:
            for attribute in attributes:  # need to make a deep copy
                self.attributes[attribute] = {k: v for k, v in attributes[attribute].items()}
                #self.attributes = copy.deepcopy(attributes)
        #print("meooow")

    def __str__(self):
        return str(self.name) + ": " + str(self.attributes)
