import copy
from re import finditer, match


class CodeTree(object):
    def __init__(self, tree=None, parent=None, lhs=None, params=None, root=None):
        self.params = params

        self.invalid = False
        self.tree = tree
        self.lhs = lhs
        self.rhs = list()
        self.root = root  # lhs nonterminal name
        self.children = list()

        # self.raw_code = None
        self.code = list()

        self.parent = parent

        self.aliases = {}
        self.symbol_table = {}

    def build(self):
        #s elf.raw_code = self.tree.raw_code
        if not self.lhs:
            self.lhs = self.set_nonterminal(self.tree.root, self.symbol_table[self.tree.root])
        self.rhs = [self.set_nonterminal(node.root, self.symbol_table[node.root]) if node.root in self.symbol_table.keys() else self.set_terminal(node.root) for node in self.tree.children]
        self.set_aliases()
        for tree_child, rhs_child in zip(self.tree.children, self.rhs):
            self.children.append(CodeTree(tree_child, self, rhs_child, params=self.params))
        #self.parse_code()
        for child in self.children:
            child.build()

    def build_node(self, nt_name, rhs_sequence, raw_code=None, processed_code=None):
        self.code = processed_code
        if not self.symbol_table:
            if not self.parent:
                self.make_symbol_table()
            else:
                self.symbol_table = self.parent.symbol_table
        if not self.lhs:
            self.lhs = self.set_nonterminal(nt_name, self.symbol_table[nt_name])
            # list of (non)terminals
        for name in rhs_sequence:
            if name[0] == "<":  # Nonterm
                self.rhs.append(self.set_nonterminal(name, self.symbol_table[name]))
            else:
                self.rhs.append(self.set_terminal(name))
        self.set_aliases()
        #if processed_code:
        #    self.code = processed_code
        #else:
        #    self.parse_code()

    def set_nonterminal(self, name, attributes=None):
        nonterminal = {"attributes": {}, "name": name}
        if not attributes and name in self.params["BNF_GRAMMAR"].non_terminals.keys():
            for attribute in self.params["BNF_GRAMMAR"].non_terminals[name]["attributes"].keys():
                nonterminal["attributes"][attribute] = {"type": None, "value": None}
        else:
            for attribute in attributes:  # need to make a deep copy
                nonterminal["attributes"][attribute] = {k: v for k, v in attributes[attribute].items()}  # k = type, va
        return nonterminal

    def set_terminal(self, name):
        return {"name": name}

    def __str__(self):
        return str(self.root) + " -> " + str(self.rhs)

    """def parse_code(self):
        if not self.raw_code:
            return
        template = "self.aliases[\"{}\"][\"attributes\"][\"{}\"][\"value\"]"
        for line in self.raw_code.splitlines():
            line = line.strip()
            if not line:
                continue
            nt_and_attr_regex = r'\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|\"(.*?)\"|(?P<subrule><[^>|\s]+>\.[A-Za-z1-9_]+)|([<]+)'
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
            self.code.append(tmp_line)"""

    def set_aliases(self):
        #if not self.raw_code:
        #    return
            # Set proper aliases
            # for example: in rule <S> ::= <S><A> we need to distinguish between first and second <S>
            # in attribute code, it is done by giving them and index: <S_1>, <S_2> etc., while <A> wont be changed
            # aliases thus are:
            # <S>   <S>   <A>
            # <S_1> <S_2> <A>
        nts_in_rule = [self.lhs["name"]]
        for token in self.rhs:
            if len(token.keys()) > 1:
                nts_in_rule.append(token["name"])

        num_of_occurrences = dict()
        aliases = list()
        for nt in nts_in_rule:
            num_of_occurrences[nt] = nts_in_rule.count(nt)
        for nt in nts_in_rule:
            if nts_in_rule.count(nt) == 1:
                aliases.append(nt)
            else:
                aliases.append(
                    "<" + nt[1:-1] + "_" + str(nts_in_rule.count(nt) - num_of_occurrences[nt] + 1) + ">")
                num_of_occurrences[nt] -= 1

        nonterminals = [self.lhs]
        for token in self.rhs:
            if len(token.keys()) > 1:
                nonterminals.append(token)

        for i in range(len(nonterminals)):
            self.aliases[aliases[i]] = nonterminals[i]

    def make_symbol_table(self):
        tmp = self.params["BNF_GRAMMAR"].non_terminals
        nts = dict()
        filename = "../grammars/"+self.params["GRAMMAR_FILE"] + ".symbols"
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
                    self.symbol_table[block[0]][name] = {"type": attribute_type.strip(), "value": default_value.strip() if type(default_value) == str else default_value}
        #print(self.symbol_table)

    def run(self):
        ntas_regex = 'self\.aliases\[\"\<[a-zA-Z1-9_]+\>\"\]\[\"attributes\"]\[\"[a-z_1-9]+\"\]\[\"value\"\]'
        run_children = False
        children_ran = False
        if not self.code:
            return
        for code_line in self.code:
            # dummy = "".join(code_line)
            nt, attribute = None, None

            # First part in the code line is a non-terminal -> this line is an assignment
            if match(ntas_regex, code_line[0]):
                nt, attribute = self._get_nt_and_var_from_code_line_part(code_line[0])
            else:
                for item in code_line:
                    if match(ntas_regex, item):
                        nt, attribute = self._get_nt_and_var_from_code_line_part(item)
            try:
                attribute_type = self.aliases[nt]["attributes"][attribute]["type"]
            except KeyError:
                print("meow")
                pass
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
                        print("\n\n"+str(repr(e))+"\n\n")
                        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

                else:
                    if not children_ran:
                        children_ran = True
                        for child in self.children:
                            # Check for leafs and perform recursive code run only if it will
                            # be applied to non-leaf
                            if child.lhs["name"] in self.symbol_table.keys():
                                child.run()
                    try:
                        exec(" ".join(code_line))
                    except Exception as e:
                        print(" ".join(code_line))
                        print(e)

        if run_children and not children_ran:
            for child in self.children:
                if child.lhs["name"] in self.symbol_table.keys():
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
        # TODO introduce attribute fitness
        self.invalid = True

    def ok(self):
        # We do not set invalid flag here 'cause we would potentially overwrite some error
        pass

    def _get_nt_and_var_from_code_line_part(self, text):
        nt = "<" + text.split("<")[1].split(">")[0] + ">"
        var = None
        var_id_regex = r'(?P<var_id>(?<=\["attributes"]\[\")[a-z\_1-9]+)'
        for regex_match in finditer(var_id_regex, text):
            if regex_match.group("var_id"):
                var = regex_match.group("var_id")
                return nt, var

    def __copy__(self, parent):
        lhs_copy = self.set_nonterminal(self.root) if len(self.lhs.keys()) > 1 else self.set_terminal(self.root)
        tree_copy = CodeTree(root=self.root, lhs=lhs_copy, parent=parent, params=self.params)

        if not self.parent:
            symbol_table_copy = {}
            for nt in self.symbol_table.keys():
                attributes = {}
                for attribute in self.symbol_table[nt].keys():
                    attributes[attribute] = {k: v for k, v in self.symbol_table[nt][attribute].items()}
                symbol_table_copy[nt] = attributes
            tree_copy.symbol_table = symbol_table_copy
        rhs_seq = (symbol["name"] for symbol in self.rhs)
        tree_copy.build_node(nt_name=self.root, rhs_sequence=rhs_seq, processed_code=self.code)

        for child in self.children:
            # Recurse through all children.
            new_child = child.__copy__(tree_copy)

            # Append the copied child to the copied parent.
            tree_copy.children.append(new_child)
        return tree_copy



class Terminal(object):
    def __init__(self, name=""):
        self.name = name

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)


class NonTerminal(object):
    def __init__(self, name="", attributes=None, params=None):
        self.params = params
        self.name = name
        self.attributes = {}
        if not attributes and name in self.params["BNF_GRAMMAR"].non_terminals.keys():
            for attribute in self.params["BNF_GRAMMAR"].non_terminals[name]["attributes"].keys():
                self.attributes[attribute] = {"type": None, "value": None}
        else:
            for attribute in attributes:  # need to make a deep copy
                self.attributes[attribute] = {k: v for k, v in attributes[attribute].items()}  # k = type, value

    def __str__(self):
        return str(self.name) + ": " + str(self.attributes)

    def __repr__(self):
        return str(self.name) + ": " + str(self.attributes)


