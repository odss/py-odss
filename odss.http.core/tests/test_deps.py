import json
import typing as t
import uuid
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
from odss.http.common import Request, RouteInfo
from pydantic import BaseModel

from odss.http.core.deps import SystemFieldType, get_dependency, resolve_dependency


async def test_empty_fn():
    def empty_fn():
        pass

    deps = get_dependency("", empty_fn)
    assert deps.fields == []
    assert deps.return_field is None

    values = await resolve_dependency(deps, {}, {})
    assert values == {}


async def test_system_params():
    def system_params_fn(req: Request, route: RouteInfo):
        pass

    deps = get_dependency("", system_params_fn)
    assert len(deps.fields) == 2
    assert deps.fields[0].name == "req"
    assert deps.fields[1].name == "route"
    assert deps.return_field is None

    values = await resolve_dependency(deps, {}, {})
    assert values == {"req": {}, "route": {}}


async def test_params_basic_types():
    def path_and_query_params_fn(
        s: str,
        i: int,
        b: bool,
        u: uuid.UUID,
        dt: datetime,
    ):
        pass

    deps = get_dependency("/{s}/{i}/{b}/{u}/{dt}", path_and_query_params_fn)

    assert len(deps.fields) == 5

    uuid4 = uuid.uuid4()
    dt = datetime.now()

    def side_effect_helper(name, defaults):
        if name == "s":
            return "string"
        elif name == "i":
            return 123
        elif name == "b":
            return True
        elif name == "u":
            return uuid4
        elif name == "dt":
            return dt

    request = MagicMock()
    request.match_info.get.side_effect = side_effect_helper
    values = await resolve_dependency(deps, request, {})
    assert values == {"s": "string", "i": 123, "b": True, "u": uuid4, "dt": dt}


async def test_params_default_value():
    def handler(name: str | None = None):
        pass

    deps = get_dependency("/{name}", handler)
    request = MagicMock()

    def side_effect_helper(key, default_value):
        return default_value

    request.match_info.get.side_effect = side_effect_helper
    values = await resolve_dependency(deps, request, {})


async def test_query_sequence_types():
    def query_sequence_params_fn(ls: list[str]):
        pass

    deps = get_dependency("", query_sequence_params_fn)

    assert len(deps.fields) == 1

    def side_effect_helper(name):
        if name == "ls":
            return ["text1", "text2"]

    request = MagicMock()
    request.query.getall.side_effect = side_effect_helper

    values = await resolve_dependency(deps, request, {})
    assert values == {"ls": ["text1", "text2"]}


def test_path_and_query_params():
    def path_and_query_params_fn(id: int, q: str = ""):
        pass

    deps = get_dependency("/{id}?q=name", path_and_query_params_fn)

    assert len(deps.fields) == 2
    assert deps.return_field is None


async def test_dataset_params():
    @dataclass
    class User:
        id: int
        name: str

    # class User(BaseModel):
    #     sid: int
    #     name: str

    def dataclass_params_fn(user: User):
        pass

    deps = get_dependency("", dataclass_params_fn)

    assert len(deps.fields) == 1
    assert deps.return_field is None

    async def side_effect_helper():
        return '{"id": 1, "name": "Bob"}'

    request = Mock()
    request.method = "POST"
    request.content_type = "application/json"
    request.read = side_effect_helper

    values = await resolve_dependency(deps, request, {})
    assert values["user"].id == 1
    assert values["user"].name == "Bob"


async def test_simple_validator_error():
    def simple_q(q: int):
        pass

    def side_effect_helper(*args):
        return "test"

    request = MagicMock()
    request.query.get.side_effect = side_effect_helper

    deps = get_dependency("", simple_q)
    with pytest.raises(Exception) as exc_info:
        await resolve_dependency(deps, request, {})

    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].location == "q"
    assert errors[0].errors[0].type == "int_parsing"
    assert (
        errors[0].errors[0].msg
        == "Input should be a valid integer, unable to parse string as an integer"
    )
    assert errors[0].errors[0].location == ""


async def test_invalid_basemodel_body():
    class Role(BaseModel):
        id: int
        name: int

    class User(BaseModel):
        id: int
        name: str
        role: Role

    def dataclass_params_fn(user: User):
        pass

    deps = get_dependency("", dataclass_params_fn)

    async def side_effect_helper():
        return json.dumps({"id": 1, "login": "Bob", "role": {"id": 1}})

    request = Mock()
    request.method = "POST"
    request.content_type = "application/json"
    request.read = side_effect_helper

    with pytest.raises(Exception) as exc_info:
        await resolve_dependency(deps, request, {})
    errors = exc_info.value.errors
    assert len(errors) == 1
    assert errors[0].msg == "ValidatorError"
    assert errors[0].location == "user"
    assert len(errors[0].errors) == 2
    assert errors[0].errors[0].type == "missing"
    assert errors[0].errors[0].location == "name"
    assert errors[0].errors[1].type == "missing"
    assert errors[0].errors[1].location == "role.name"


async def test_invalid_dataset_params():
    @dataclass
    class Role:
        id: int
        name: int

    @dataclass
    class Profile:
        email: bool
        website: bool

    @dataclass
    class User:
        id: int
        name: str
        role: Role
        profile: Profile

    def dataclass_params_fn(user: User):
        pass

    deps = get_dependency("", dataclass_params_fn)

    async def side_effect_helper():
        return json.dumps(
            {
                "id": 1,
                "name": "Bob",
                "profile": {
                    "website": "http://example.com",
                    "email": "email@example.com",
                },
                "role": {"id": 1, "name": "admin"},
            }
        )

    request = Mock()
    request.method = "POST"
    request.content_type = "application/json"
    request.read = side_effect_helper

    with pytest.raises(Exception) as exc_info:
        await resolve_dependency(deps, request, {})
    errors = exc_info.value.errors
    assert len(errors) == 1
    error = errors[0]
    assert error.location == "user"
    assert len(error.errors) == 3
    # assert error.errors[0].msg == "value is not a valid integer"
    assert error.errors[0].type == "int_parsing"
    assert error.errors[0].location == "role.name"

    # assert error.errors[1].msg == "value could not be parsed to a boolean"
    assert error.errors[1].type == "bool_parsing"
    assert error.errors[1].location == "profile.email"

    # assert error.errors[2].msg == "value could not be parsed to a boolean"
    assert error.errors[2].type == "bool_parsing"
    assert error.errors[2].location == "profile.website"


def test_return_fn():
    def simple_test() -> str:
        return "test"

    deps = get_dependency("", simple_test)
    assert deps.return_field is not None
