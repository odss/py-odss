import uuid
import json
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import Mock, MagicMock

import pytest

from odss.http.common import Request, RouteInfo
from odss.http.core.deps import get_dependency, resolve_dependency, SystemFieldType


async def test_empty_fn():
    def empty_fn():
        pass

    deps = get_dependency("", empty_fn)
    assert deps.path_fields == []
    assert deps.query_fields == []
    assert deps.params_fields == []
    assert deps.system_fields == []
    assert deps.body_field is None
    assert deps.return_field is None

    values, errors = await resolve_dependency(deps, {}, {})
    assert values == {}
    assert errors == []


async def test_system_params():
    def system_params_fn(req: Request, route: RouteInfo):
        pass

    deps = get_dependency("", system_params_fn)
    assert deps.path_fields == []
    assert deps.query_fields == []
    assert deps.params_fields == []
    assert len(deps.system_fields) == 2
    assert deps.system_fields[0].kind == SystemFieldType.REQUEST
    assert deps.system_fields[0].name == "req"
    assert deps.system_fields[1].kind == SystemFieldType.ROUTE_INFO
    assert deps.system_fields[1].name == "route"

    assert deps.body_field is None
    assert deps.return_field is None

    values, errors = await resolve_dependency(deps, {}, {})
    assert values == {"req": {}, "route": {}}
    assert errors == []


async def test_params_singleton_types():
    def path_and_query_params_fn(s: str, i: int, b: bool, u: uuid.UUID, dt: datetime):
        pass

    deps = get_dependency("/{s}/{i}/{b}/{u}/{dt}", path_and_query_params_fn)

    assert len(deps.path_fields) == 5

    assert deps.path_fields[0].name == "s"
    assert deps.path_fields[0].type_ == str
    assert deps.path_fields[0].required
    assert deps.path_fields[0].default is None

    assert deps.path_fields[1].name == "i"
    assert deps.path_fields[1].type_ == int
    assert deps.path_fields[1].required
    assert deps.path_fields[1].default is None

    assert deps.path_fields[2].name == "b"
    assert deps.path_fields[2].type_ == bool
    assert deps.path_fields[2].required
    assert deps.path_fields[2].default is None

    assert deps.path_fields[3].name == "u"
    assert deps.path_fields[3].type_ == uuid.UUID
    assert deps.path_fields[3].required
    assert deps.path_fields[3].default is None

    assert deps.path_fields[4].name == "dt"
    assert deps.path_fields[4].type_ == datetime
    assert deps.path_fields[4].required
    assert deps.path_fields[4].default is None

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
    values, errors = await resolve_dependency(deps, request, {})
    assert values == {"s": "string", "i": 123, "b": True, "u": uuid4, "dt": dt}
    assert errors == []


async def test_query_sequence_types():
    def query_sequence_params_fn(ls: list[str]):
        pass

    deps = get_dependency("", query_sequence_params_fn)

    assert len(deps.query_fields) == 1

    def side_effect_helper(name):
        if name == "ls":
            return ["text1", "text2"]

    request = MagicMock()
    request.query.getall.side_effect = side_effect_helper

    values, errors = await resolve_dependency(deps, request, {})
    assert values == {"ls": ["text1", "text2"]}
    assert errors == []


def test_path_and_query_params():
    def path_and_query_params_fn(id: int, q: str = ""):
        pass

    deps = get_dependency("/{id}?q=name", path_and_query_params_fn)

    assert len(deps.path_fields) == 1

    assert deps.path_fields[0].name == "id"
    assert deps.path_fields[0].type_ == int
    assert deps.path_fields[0].required
    assert deps.path_fields[0].default is None

    assert len(deps.query_fields) == 1
    assert deps.query_fields[0].name == "q"
    assert deps.query_fields[0].type_ == str
    assert not deps.query_fields[0].required
    assert deps.query_fields[0].default == ""

    assert deps.params_fields == []
    assert deps.system_fields == []
    assert deps.body_field is None
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

    assert deps.path_fields == []
    assert deps.query_fields == []
    assert deps.params_fields == []
    assert deps.system_fields == []
    assert deps.body_field is not None
    assert deps.body_field.name == "user"
    assert deps.body_field.type_ == User
    assert deps.body_field.required

    assert deps.return_field is None

    async def side_effect_helper():
        return '{"id": 1, "name": "Bob"}'

    request = Mock()
    request.method = "POST"
    request.content_type = "application/json"
    request.read = side_effect_helper

    values, errors = await resolve_dependency(deps, request, {})
    assert errors == []
    assert values["user"].id == 1
    assert values["user"].name == "Bob"


def test_wrong_param_type():
    def path_list_param_fn(ls: list[str]):
        pass

    with pytest.raises(TypeError):
        get_dependency("/{ls}", path_list_param_fn)


async def test_simple_validator_error():
    def simple_q(q: int):
        pass

    def side_effect_helper(*args):
        return "test"

    request = MagicMock()
    request.query.get.side_effect = side_effect_helper

    deps = get_dependency("", simple_q)
    _, errors = await resolve_dependency(deps, request, {})
    assert len(errors) == 1
    assert errors[0].msg == "value is not a valid integer"
    assert errors[0].location == "q"


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

    # class User(BaseModel):
    #     sid: int
    #     name: str

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

    _, errors = await resolve_dependency(deps, request, {})

    assert len(errors) == 1
    error = errors[0]
    assert error.location == "user"
    assert len(error.errors) == 3
    assert error.errors[0].msg == "value is not a valid integer"
    assert error.errors[0].type == "type_error.integer"
    assert error.errors[0].location == "role.name"

    assert error.errors[1].msg == "value could not be parsed to a boolean"
    assert error.errors[1].type == "type_error.bool"
    assert error.errors[1].location == "profile.email"

    assert error.errors[2].msg == "value could not be parsed to a boolean"
    assert error.errors[2].type == "type_error.bool"
    assert error.errors[2].location == "profile.website"


def test_return_fn():
    def simple_test() -> str:
        return "test"

    deps = get_dependency("", simple_test)
    assert deps.return_field is not None
