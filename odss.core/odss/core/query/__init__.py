from . import nodes, parser

TQuery = nodes.Node | dict | str | None

def create_query(query: TQuery):
    if query is None:
        return nodes.AllNode()

    if isinstance(query, nodes.Node):
        return query

    if isinstance(query, dict):
        return _build_query(query)

    if isinstance(query, str):
        return parser.parse_query(query)

    raise TypeError('Unknown filter type: "{}"'.format(type(query)))


def _build_query(rules):
    node = nodes.AndNode()
    for name, value in rules.items():
        if isinstance(value, (list, tuple)):
            sub = nodes.OrNode()
            for v in value:
                sub.value.append(nodes.EqNode(v, name))
            if sub.value:
                node.value.append(sub.value[0])
            else:
                node.value.append(sub)
        else:
            node.value.append(nodes.EqNode(value, name))
    if len(node.value) == 1:
        return node.value[0]
    return node
