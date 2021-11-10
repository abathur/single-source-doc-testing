#!/usr/bin/env python3
import sys
import operator
from functools import singledispatchmethod

import tinycss2, cssselect2

import dmark

# TODO: handle better than just global state?
content = matcher = None
SORT_KEY = operator.itemgetter(0, 1)


class StyleMatcher(cssselect2.Matcher):
    @staticmethod
    def token_to_value(value):
        if isinstance(value, tinycss2.ast.NumberToken):
            return value.int_value or value.value
        else:
            return value.value

    def __init__(self, css):
        cssselect2.Matcher.__init__(self)
        rules = tinycss2.parse_stylesheet_bytes(
            css,
            skip_whitespace=True,
            skip_comments=True,
        )[0]

        for rule in rules:
            for selector in cssselect2.compile_selector_list(rule.prelude):
                self.add_selector(
                    selector,
                    {
                        obj.name: self.token_to_value(
                            tinycss2.parse_one_component_value(
                                obj.value,
                                skip_comments=True,
                            )
                        )
                        for obj in tinycss2.parse_declaration_list(
                            rule.content, skip_whitespace=True
                        )
                        if obj.type == "declaration"
                    },
                )

    def match(self, element):
        relevant_selectors = []

        for class_name in element.attributes.keys():
            relevant_selectors.append(self.class_selectors.get(class_name, []))

        relevant_selectors.append(
            self.lower_local_name_selectors.get(element.name.lower(), [])
        )
        relevant_selectors.append(self.other_selectors)

        results = [
            (specificity, order, pseudo, payload)
            for selector_list in relevant_selectors
            for test, specificity, order, pseudo, payload in selector_list
            if test(element)
        ]

        results.sort(key=SORT_KEY)
        return results


def space_cadet(nodes):
    """
    Lay out a sequence of nodes as a sequence of strings.

    Yield trimmed node text and appropriate boundary
    whitespace strings.
    """
    nodes = [x for x in nodes if x]
    prev = cur = None
    cur = nodes.pop(0)
    yield cur.left(None)

    while len(nodes):
        prev = cur
        cur = nodes.pop(0)
        bound = prev.right(cur)
        yield prev.text
        yield bound

    bound = cur.right(None)
    yield cur.text
    yield bound


class OutputForm(object):
    text = style = depth = None
    space = strippable = lstrippable = rstrippable = None

    def __init__(self, style, text, depth):
        self.text = text
        self.style = style
        if "strippable" in style:
            self.strippable = style["strippable"]
        if "lstrippable" in style:
            self.lstrippable = style["lstrippable"]
        if "rstrippable" in style:
            self.rstrippable = style["rstrippable"]
        if "space" in style:
            self.space = style["space"] * style.get("spacen", 1)
        self.depth = depth

    def __repr__(self):
        return "<{:} == {:}>".format(self.__class__.__name__, repr(self.text))

    def rstrip(self):
        self.text = self.text.rstrip(self.rstrippable or self.strippable)

    def rstrip_other(self, other):
        if other and hasattr(other, "rstrip"):
            return other.rstrip()

    def lstrip(self):
        self.text = self.text.lstrip(self.lstrippable or self.strippable)

    def lstrip_other(self, other):
        if other and hasattr(other, "lstrip"):
            return other.lstrip()

    # singledispatched per class later
    def left(self, other):
        raise NotImplementedError("I don't know this", type(other))

    def _left(self, other):
        self.lstrip()
        self.rstrip_other(other)
        return self.space

    def right(self, other):
        raise NotImplementedError("I don't know this", type(other))

    def _right_dominated(self, other):
        # defer to the higher-order unit
        return other.left(self)

    def _right_dominating(self, other):
        self.lstrip_other(other)
        self.rstrip()
        return self.space


class Char(OutputForm):
    space = ""

    def _right_dominating(self, other):
        # override; I think only strip char when dominated
        return self.space

    def __bool__(self):
        # filterable if all-space
        return len(self.text.strip(" ")) > 0


class Word(OutputForm):
    space = " "


class Line(OutputForm):
    space = "\n"


class Block(OutputForm):
    space = "\n\n"


OUTPUT_FORMS = {
    "char": Char,
    "word": Word,
    "line": Line,
    "block": Block,
}


def form_from_style(style, content, depth):
    try:
        form = OUTPUT_FORMS[style.get("display", "block")]
        return form(style, content, depth)
    except KeyError as e:
        raise Exception(
            "I only recognize the following display values: %s"
            % ", ".join(OUTPUT_FORMS.keys())
        ) from e


"""
Set up single-dispatch methods on all of these OutputForm classes for
all of the other OutputForm classes.
"""
for form in OUTPUT_FORMS.values():
    dominating = True
    form.left = singledispatchmethod(form.left)
    form.right = singledispatchmethod(form.right)
    for typ in (type(None), str, Char, Word, Line, Block):
        if dominating:
            form.left.register(typ, form._left)
            form.right.register(typ, form._right_dominating)
        else:
            form.right.register(typ, form._right_dominated)

        if typ == form:
            dominating = False


class WordsWurst(dmark.Translator):
    @classmethod
    def handle_string(cls, string, context):
        depth = context.get("depth", 1)
        return Char({}, string, depth)

    @classmethod
    def handle_styled(cls, element, context, depth):
        output = []
        style = {}
        before = after = content = ""
        matches = matcher.match(element)
        if matches:
            for match in matches:
                """
                specificity is a 3-tuple of unknown values
                    0 = number of ID selectors
                    1 = number of class selectors, attributes selectors, and pseudo-classes
                    2 = number of type selectors and pseudo-elements
                order probably reflects add_selector order
                sort should be 0 > 1 > 2 > order
                """
                specificity, order, pseudo, declarations = match
                if pseudo:
                    if pseudo not in style:
                        style[pseudo] = declarations.copy()
                    else:
                        style[pseudo].update(declarations)
                else:
                    style.update(declarations)

        if "before" in style and "content" in style["before"]:
            output.append(
                form_from_style(style["before"], style["before"]["content"], depth)
            )

        content = (
            style["content"]
            if "content" in style
            else "".join(
                space_cadet(
                    cls.handle_children(element, dict(context, depth=depth + 1))
                )
            )
        )

        output.append(Char({}, content, depth))

        if "after" in style and "content" in style["after"]:
            output.append(
                form_from_style(style["after"], style["after"]["content"], depth)
            )

        return form_from_style(style, "".join(space_cadet(output)), depth)

    @classmethod
    def handle_compose(cls, element, context, depth):
        global content, matcher
        content_path, style_path = element.children.pop(0).split()
        with open(content_path, "r") as cd, open(style_path, "rb") as sd:
            content_file = cd.read()
            style_file = sd.read()

        content = dmark.Parser(content_file).parse()
        for item in content:
            item.associate()

        matcher = StyleMatcher(style_file)
        return "".join(
            space_cadet(cls.handle_children(element, dict(context, depth=depth + 1)))
        )

    @classmethod
    def handle_select(cls, element, context, depth):
        global content, matcher
        selected = []
        query = element.children.pop(0)
        for part in content:
            result = part.query(query)
            if result:
                selected.append(
                    cls.handle_element(result, dict(context, depth=depth + 1))
                )
        if selected:
            # strip to keep selected nodes in the ~envelope
            # of the original select directive.
            return Char({}, "".join(space_cadet(selected)).strip(), depth)
        else:
            raise Exception("[[bad select]]", element)

    @classmethod
    def handle_element(cls, element, context):
        depth = context.get("depth", 1)
        if element.name == "compose":
            return cls.handle_compose(element, context, depth)
        elif element.name == "select":
            return cls.handle_select(element, context, depth)
        else:
            return cls.handle_styled(element, context, depth)


class Element(dmark.Element, cssselect2.ElementWrapper):
    local_name = parent = index = in_html_document = None
    etree_element = etree_siblings = transport_content_language = None

    def __init__(self, name, attributes, children):
        self.name = name
        self.attributes = attributes
        self.children = children
        self.etree_element = self
        self.local_name = name
        self.in_html_document = False

    def get(self, key):
        return self.attributes.get(key, None)

    def associate(self):
        """
        Would prefer to do this without our own full tree visit,
        whether that's at __init__, or via an add_child hook, or
        via a children-added callback
        """
        for i, child in enumerate(self.children):
            if not isinstance(child, Element):
                continue
            if i > 0:
                child.previous = self.children[i - 1]

            child.parent = self
            child.etree_siblings = self.children
            child.index = i
            child.associate()

    def iter_children(self):
        """
        override ElementWrapper.iter_children
        to use d-mark Element.children
        """
        for child in self.children:
            yield child

    def iter_subtree(self):
        """
        override ElementWrapper.iter_subtree
        to handle non-Elements such as str
        """
        stack = [iter([self])]
        while stack:
            element = next(stack[-1], None)
            if element is None:
                stack.pop()
            elif not isinstance(element, Element):
                continue
            else:
                yield element
                stack.append(element.iter_children())

    def etree_children(self):
        """
        override ElementWrapper.etree_children
        to use d-mark Element.children
        """
        return self.children


# monkey patching
dmark.Element = Element

for arg in sys.argv[1:]:
    with open(arg, "r") as fd:
        idkmybffjill = fd.read()
    tree = dmark.Parser(idkmybffjill).parse()
    # TODO: not certain about lstrip here
    print(WordsWurst.translate(tree).lstrip())
