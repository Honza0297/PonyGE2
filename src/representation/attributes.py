import re

#from algorithm.parameters import params
from re import DOTALL, MULTILINE, finditer, match

productionpartsregex = '\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|"(.*?)"|(?P<subrule><[^>|\s]+>)|([<]+)'


class AttrCode():
    def __init__(self, code, tree):
        # get a reference to the tree/node this instance is part of
        if tree is not None:
            from representation.tree import Tree
            self.tree = tree
        # lhs is the NT on the LHS of corresponding rule, AKA the root of the tree
        self.lhs = NontermAttrs(self.tree.root,
                                None if self.tree.root not in params["BNF_GRAMMAR"].non_terminals.keys() else
                                params["BNF_GRAMMAR"].non_terminals[self.tree.root]["attributes"])

        self.aliases = {}

        self.exec_code = list()
        self.raw_code = None
        self.valid = True

        self.set_attr_code(code)

    def attrs_init(self, non_recursive=False):
        """Init attribute tree"""
        # Some nodes have no code - leafs etc.
        if not self.raw_code:
            return
        # Set proper aliases
        # for example: in rule <S> ::= <S><A> we need to distinguish between first and second <S>
        # in attribute code, it is done by giving them and index: <S_1>, <S_2> etc., while <A> wont be changed
        # aliases thus are:
        # <S>   <S>   <A>
        # <S_1> <S_2> <A>
        nts_in_rule = [self.lhs] + [child.attr_code.lhs for child in self.tree.children]
        nt_names_in_rule = [self.tree.root] + [child.root for child in self.tree.children]
        for nt in nts_in_rule:
            if nt_names_in_rule.count(nt.name) > 1:
                count = 1
                for nnt in nts_in_rule:
                    if nnt.name == nt.name:
                        self.aliases[nnt.name[:-1] + "_{}>".format(count)] = nnt
                        count += 1
            else:
                self.aliases[nt.name] = nt
        # set whether the attributes are syntesized or inherited for current LHS
        for line in self.raw_code.splitlines():
            line = line.strip()
            # returns string in a form of NT.attr_name (<A>.val, <S_1>.itemcount_3 etc.).
            # Only alphanumeric characters and underscore (_) are allowed in attribute name
            nt_and_attr_regex = '\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|"(.*?)"|(?P<subrule><[^>|\s]+>\.[A-Za-z1-9_]+)|([<]+)'

            first = True
            for ntas in finditer(nt_and_attr_regex, line):
                if not ntas.group("subrule"):
                    continue
                nt, attr = ntas.group("subrule").split(".")
                # if the first processed attribute seems to belong to the lhs of current rule, suppose it is synthesized
                if self.aliases[nt] == self.lhs and first and self.aliases[nt].attrs[attr]["type"] is None:
                    self.aliases[nt].attrs[attr]["type"] = "S"  # attribute is syntesized
                # else if it is not current lhs, this attribute is probably inherited
                elif self.aliases[nt] != self.lhs and first and self.aliases[nt].attrs[attr]["type"] is None:
                    # check whether it is a constant/literal assignment or not
                    line_iter = finditer(nt_and_attr_regex, line)
                    line_iter.__next__()  # throw off the first part
                    next_part = line_iter.__next__().group(0).strip()
                    if "=" in next_part and next_part.strip() != "=":
                        next_node = self.get_child(nt)
                        if next_node:
                            next_node.attr_code.attrs_init(non_recursive=True)
                            self.aliases[nt].attrs[attr]["type"] = next_node.attr_code.lhs.attrs[attr]["type"]
                            # if there was no mention about the current attribute in next level, it is probably
                            # some value to compare with (capacity in knapsack problem etc)
                            if next_node.attr_code.lhs.attrs[attr]["type"] is None:
                                next_node.attr_code.lhs.attrs[attr]["type"] = "I"

                    else:
                        self.aliases[nt].attrs[attr]["type"] = "I"
                first = False
                if not first:
                    break

        if non_recursive:
            return

        template = "self.aliases[\"{}\"].attrs[\"{}\"][\"value\"]"
        for line in self.raw_code.splitlines():
            if not line.strip():
                continue
            nt_and_attr_regex = '\ *([\r\n]+)\ *|([^\'"<\r\n]+)|\'(.*?)\'|"(.*?)"|(?P<subrule><[^>|\s]+>\.[A-Za-z1-9_]+)|([<]+)'
            tmp_line = list()
            for ntas in finditer(nt_and_attr_regex, line):
                dummy = ntas.group(0)
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

            self.exec_code.append(tmp_line)

        for child in self.tree.children:
            child.attr_code.attrs_init()

    def set_attr_code(self, code):
        if code is not None:
            # strip leading and ending {}
            self.raw_code = code.strip()[1:-1]

    def run(self):
        ntas_regex = "self\.aliases\[\"\<[a-zA-Z1-9_]+\>\"\]\.attrs\[\"[a-z_1-9]+\"\]\[\"value\"\]"
        run_children = False
        children_ran = False
        for code_line in self.exec_code:
            #dummy = "".join(code_line)
            nt, var = None, None

            # First part in the code line is a non-terminal -> this line is and assignment
            if match(ntas_regex, code_line[0]):
                nt, var = self._get_nt_and_var_from_code_line_part(code_line[0])
            else:
                for item in code_line:
                    if match(ntas_regex, item):
                        nt, var = self._get_nt_and_var_from_code_line_part(item)
            attribute_type = self.aliases[nt].attrs[var]["type"]
            if attribute_type == "I":
                try:
                    exec(" ".join(code_line))
                    run_children = True
                except Exception as e:
                    print(" ".join(code_line))
                    print(e)
                    exit(-1)
            elif attribute_type == "S":
                # check whether it is a literal assignment - in that case, treat it like "I" type
                # in case if literal assignment, the = and literal are parsed as one token -> check length should be ok
                if len(code_line[1].strip()) > 1:
                    try:
                        exec(" ".join(code_line))
                        run_children = True
                    except Exception as e:
                        print(" ".join(code_line))
                        print(e)
                        exit(-1)
                else:
                    children_ran = True
                    for child in self.tree.children:
                        # Check for leafs and perform recursive code run only if it will
                        # be applied to non-leaf
                        if child.root in params["BNF_GRAMMAR"].non_terminals.keys():
                            child.attr_code.run()
                    try:
                        exec(" ".join(code_line))
                    except Exception as e:
                        print(" ".join(code_line))
                        print(e)
                        exit(-1)

        if run_children and not children_ran:
            for child in self.tree.children:
                child.attr_code.run()




    def error(self):
        self.valid = False
        #print("EEEERRRROOOORRRR")

    def ok(self):
        pass
        #print("OOOKKK")

    def _get_nt_and_var_from_code_line_part(self, text):
        nt = "<" + text.split("<")[1].split(">")[0] + ">"
        var = None
        var_id_regex = r'(?P<var_id>(?<=\.attrs\[\")[a-z\_1-9]+)'
        for regex_match in finditer(var_id_regex, text):
            if regex_match.group("var_id"):
                var = regex_match.group("var_id")
                return nt, var

    def get_child(self, nonterm):
        for c in self.tree.children:
            if c.root == nonterm:
                return c
        return None


class NontermAttrs():
    def __init__(self, name, attrs=None):
        self.name = name
        self.attrs = {}
        if attrs is not None:
            for attr in attrs:
                self.attrs[attr] = {"type": None, "value": None}

    def set_attr(self, name, val=None, attr_type=None):
        self.attrs[name]["value"] = val
        if type is not None:
            self.attrs[name]["type"] = attr_type
