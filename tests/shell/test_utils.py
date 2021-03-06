from odss.shell.utils import make_ascii_table


def test_create_simple_ascii_table():
    headers = ["ID", "Name", "Value"]
    records = (
        (1, "Test1", 10),
        (2, "Test2", 20),
        (3, "Test3", 30),
    )
    output = make_ascii_table(headers, records)
    expected = clean_text(
        """
        ┌────┬───────┬───────┐
        │ ID │ Name  │ Value │
        ├────┼───────┼───────┤
        │ 1  │ Test1 │ 10    │
        │ 2  │ Test2 │ 20    │
        │ 3  │ Test3 │ 30    │
        └────┴───────┴───────┘
    """
    )
    assert output == expected


def clean_text(text):
    return "\n".join([line.strip() for line in text.strip().split("\n")])
