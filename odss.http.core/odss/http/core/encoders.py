import datetime
import decimal
import enum
import pathlib
from types import GeneratorType
import typing as t
import dataclasses as dc
import uuid


def serialize_response(obj: t.Any) -> bytes:
    return serialize_to_jsonable(obj)


def serialize_to_jsonable(obj: t.Any):
    if dc.is_dataclass(obj):
        return serialize_to_jsonable(dc.asdict(obj))

    if obj is None:
        return None

    if isinstance(obj, (str, int, float)):
        return obj

    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            new_dict[serialize_to_jsonable(key)] = serialize_to_jsonable(value)
        return new_dict

    if isinstance(obj, (list, set, tuple, GeneratorType)):
        return tuple(serialize_to_jsonable(item) for item in obj)

    for base in obj.__class__.__mro__[:-1]:
        try:
            return ENCODERS[base](obj)
        except KeyError:
            pass

    raise TypeError("Unknow serialized type: {}".format(type(obj)))


def isoformat(obj: t.Union[datetime.date, datetime.time]) -> str:
    return obj.isoformat()


def decimal_encoder(d: decimal.Decimal) -> int | float:
    return int(d) if d.as_tuple().exponent >= 0 else float(d)


ENCODERS: dict[t.Type[t.Any], t.Callable[[t.Any], t.Any]] = {
    bytes: lambda o: o.decode(),
    datetime.date: isoformat,
    datetime.datetime: isoformat,
    datetime.time: isoformat,
    datetime.timedelta: lambda td: td.total_seconds(),
    pathlib.Path: str,
    uuid.UUID: str,
    enum.Enum: lambda e: e.value,
    decimal.Decimal: decimal_encoder,
}
