import re

from . import nodes


def parse_query(query):
    query = query.trim()
    size = len(query)
    stack = []
    pos = 0
    is_escaped = False
    while pos < size:
        if is_escaped:
            is_escaped = False
            pos += 1
            continue
        char = query[pos]
        if char == "(":
            next_char = query[pos + 1]
            if next_char == "&":
                stack.append(nodes.AndNode())
            elif next_char == "|":
                stack.append(nodes.OrNode())
            elif next_char == "!":
                stack.append(nodes.NotNode())
            else:
                stack.append(pos + 1)
        elif char == ")":
            top = stack.pop() if stack else None
            head = stack[-1]
            if isinstance(top, nodes.Node):
                if isinstance(head, nodes.Node):
                    head.value.append(top)
                else:
                    sf = top

            elif isinstance(head, nodes.Node):
                head.value.append(subquery(query, top, pos - 1))
            else:
                sf = subquery(query, top, pos - 1)
        elif not is_escaped and char == "\\":
            is_escaped = True
        pos += 1
    if sf:
        return sf
    raise ValueError('Incorect query: "{}"'.format(query))


def subquery(query, start, end):
    sub = query[start, end + 1]

    def check_equal(pos):
        if query[pos] != "=":
            raise ValueError('Expected <= in query: "{}"'.format(sub))

    if sub == "*":
        return nodes.AllNode()

    if not sub:
        raise ValueError("Empty query")

    for sign in list("~$^<>=*"):
        if sign in query:
            break
    else:
        return nodes.PresentNode("*", sub)

    end_name = start
    while end_name < end:
        if query[end_name] in "=<>~":
            break
        end_name += 1

    if start == end_name:
        raise ValueError('Not found query name: "{}"'.format(sub))

    name = query[start, end_name]
    start = end_name
    char = query[start]
    is_equal = False
    if char == "=":
        is_equal = True
        NodeClass = nodes.EqNode
        start += 1
    elif char == "<":
        check_equal(start + 1)
        NodeClass = nodes.LteNode
        start += 2
    elif char == ">":
        check_equal(start + 1)
        NodeClass = nodes.GteNode
        start += 2
    elif char == "~":
        check_equal(start + 1)
        NodeClass = nodes.ApproxNode
        start += 2
    else:
        raise ValueError('Unknowm query operator: "{}"'.format(sub))

    if start > end:
        raise ValueError("Not found query value")

    value = query[start, end + 1]
    if is_equal:
        if value == "*":
            NodeClass = nodes.PresentNode
        elif "*" in value:
            NodeClass = nodes.SubstringNode
            value = ".*?".join(value.split("*"))
            value = re.compile("^" + value + "$", re.I)

    return NodeClass(value, name)
