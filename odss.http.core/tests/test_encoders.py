from dataclasses import dataclass, field
import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID
import pytest

from odss.http.core.encoders import serialize_to_jsonable


datetime_now = datetime.datetime.now()
date_today = datetime.date.today()
delta = datetime.timedelta(1000)


@pytest.mark.parametrize(
    "obj,expected",
    [
        (None, None),
        ("test", "test"),
        (b"bytes", "bytes"),
        (8, 8),
        (1.2, 1.2),
        (
            UUID("ecaa455c-aac8-4882-a63c-4def9a7d22ef"),
            "ecaa455c-aac8-4882-a63c-4def9a7d22ef",
        ),
        (datetime_now, datetime_now.isoformat()),
        (date_today, date_today.isoformat()),
        (delta, delta.total_seconds()),
        (Decimal(1), 1),
        (Path("/home/user1"), "/home/user1"),
        (Decimal(1.2), 1.2),
        ([1, 2.2, None, "test"], (1, 2.2, None, "test")),
        ({"a": 1, "b": 2}, {"a": 1, "b": 2}),
    ],
)
def test_simple_values(obj, expected):
    assert serialize_to_jsonable(obj) == expected


def test_enum():
    class Kind(Enum):
        FIRST = 1
        LAST = 2

    assert serialize_to_jsonable(Kind.FIRST) == 1


def test_complex():
    class E1(Enum):
        FIRST = 1
        LAST = 2

    @dataclass
    class S1:
        int_1: int = 1
        float_1: float = 2.2
        str_1: str = "text"
        e_1: E1 = E1.FIRST
        uuid_1: UUID = UUID("ecaa455c-aac8-4882-a63c-4def9a7d22ef")

    @dataclass
    class S2:
        int_1: int = 1
        float_1: float = 2.2
        str_1: str = "text"
        list_1: list = field(default_factory=list)
        s_1: S1 = field(default_factory=S1)

    assert serialize_to_jsonable(S2()) == {
        "int_1": 1,
        "float_1": 2.2,
        "str_1": "text",
        "list_1": tuple(),
        "s_1": {
            "int_1": 1,
            "float_1": 2.2,
            "str_1": "text",
            "e_1": 1,
            "uuid_1": "ecaa455c-aac8-4882-a63c-4def9a7d22ef",
        },
    }
