from odss.core.query import create_query


def test_parse_eq():
    node = create_query("(foo=bar)")
    assert node is not None
    assert node.match({"foo": "bar"})
    assert not node.match({"bar": "foo"})


def test_parse_eq_without():
    node = create_query("foo=bar")
    assert node is not None
    assert node.match({"foo": "bar"})
    assert not node.match({"bar": "foo"})


def test_parse_all():
    node = create_query("(*)")
    assert node is not None
    assert node.match({"foo": "bar"})
    assert node.match({"bar": "foo"})


def test_parse_present():
    node = create_query("(foo)")
    assert node is not None
    assert node.match({"foo": "bar"})
    assert not node.match({"bar": "foo"})
