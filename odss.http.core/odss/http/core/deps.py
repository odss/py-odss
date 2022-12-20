from collections import namedtuple
import inspect
import re
import typing as t
import dataclasses as dc

from pydantic import BaseModel, BaseConfig
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from pydantic.errors import PydanticTypeError, PydanticValueError
from pydantic.fields import (
    ModelField,
    FieldInfo,
    SHAPE_SINGLETON,
    SHAPE_LIST,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
)
from odss.http.common import Request, RouteInfo, decode_json, HTTPException

sequence_shapes = (
    SHAPE_LIST,
    SHAPE_SET,
    SHAPE_TUPLE,
    SHAPE_TUPLE_ELLIPSIS,
)

sequence_types = (list, set, tuple)


class SystemFieldType:
    REQUEST = "request"
    ROUTE_INFO = "route-info"


@dc.dataclass
class SystemField:
    kind: SystemFieldType
    name: str


@dc.dataclass
class Dependency:
    path_fields: list[ModelField] = dc.field(default_factory=list)
    query_fields: list[ModelField] = dc.field(default_factory=list)
    params_fields: list[ModelField] = dc.field(default_factory=list)
    system_fields: list[SystemField] = dc.field(default_factory=list)
    body_field: ModelField = None
    return_field: t.Any = None


def get_dependency(path, handler: t.Callable) -> Dependency:
    path_param_names = set(re.findall("{(.*?)}", path))
    handler_signature = inspect.signature(handler)
    deps = Dependency()
    for param in handler_signature.parameters.values():
        if check_system_field(deps, param):
            continue

        field = create_model_field(param)
        if field.name in path_param_names:
            if is_scalar_field(field):
                deps.path_fields.append(field)
            else:
                raise TypeError(f'Not supported param type in field "{field.name}"')
        elif is_body_field(field) and not deps.body_field:
            deps.body_field = field
        elif is_scalar_field(field) or is_sequence_scalar_field(field):
            deps.query_fields.append(field)
        else:
            raise TypeError(f'Unknown type: "{field.type_}" in field: "{field.name}"')
            # deps.params_fields.append(field)

    deps.return_field = (
        handler_signature.return_annotation
        if handler_signature.return_annotation != inspect._empty
        else None
    )
    return deps


def check_system_field(deps: Dependency, param: inspect.Parameter) -> bool:
    if param.annotation == Request:
        deps.system_fields.append(SystemField(SystemFieldType.REQUEST, param.name))
        return True
    elif param.annotation == RouteInfo:
        deps.system_fields.append(SystemField(SystemFieldType.ROUTE_INFO, param.name))
        return True
    return False


def create_model_field(param: inspect.Parameter):
    annotation = param.annotation if param.annotation != inspect._empty else t.Any
    default_value = None
    required = True
    if param.default != param.empty:
        default_value = param.default
        required = False

    return ModelField(
        name=param.name,
        type_=annotation,
        default=default_value,
        required=required,
        class_validators={},
        model_config=BaseConfig,
        field_info=FieldInfo(),
        # alias=alias,
    )


def is_scalar_field(field: ModelField) -> bool:
    return field.shape == SHAPE_SINGLETON or dc.is_dataclass(field.type_)


def is_sequence_scalar_field(field: ModelField) -> bool:
    if field.shape in sequence_shapes:
        if field.sub_fields is not None:
            return all(is_scalar_field(sub_field) for sub_field in field.sub_fields)
    return False


def is_body_field(field: ModelField) -> bool:
    if issubclass(field.type_, BaseModel) or dc.is_dataclass(field.type_):
        return True


async def resolve_dependency(
    deps: Dependency, request: Request, props
) -> dict[str, t.Any]:
    values = {}
    all_errors = []

    for field in deps.system_fields:
        if field.kind == SystemFieldType.REQUEST:
            values[field.name] = request
        elif field.kind == SystemFieldType.ROUTE_INFO:
            values[field.name] = props

    for field in deps.path_fields:
        value = request.match_info.get(field.name, field.default)

        valid_value, errors = field.validate(value, values, loc=field.name)
        if errors:
            if isinstance(errors, list):
                all_errors.extend(errors)
            else:
                all_errors.append(errors)
        else:
            values[field.name] = valid_value

    for field in deps.query_fields:
        value = None
        if is_scalar_field(field):
            value = request.query.get(field.name, field.default)
        elif is_sequence_scalar_field(field):
            value = request.query.getall(field.name)

        valid_value, errors = field.validate(value, values, loc=field.name)
        if errors:
            if isinstance(errors, list):
                all_errors.extend(errors)
            else:
                all_errors.append(errors)
        else:
            values[field.name] = valid_value

    if deps.body_field:
        value = None
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            if request.content_type == "application/json":
                data = await request.read()
                value = decode_json(data)
            else:
                value = await request.post()

        valid_value, errors = deps.body_field.validate(
            value, values, loc=deps.body_field.name
        )
        if errors:
            if isinstance(errors, list):
                all_errors.extend(errors)
            else:
                all_errors.append(errors)

        values[deps.body_field.name] = valid_value
    if all_errors:
        all_errors = list(format_errors(all_errors))
    return values, all_errors


ErrorInfo = namedtuple("ValidInfo", "msg,type,location")


@dc.dataclass
class ResolveError:
    msg: str
    location: tuple[str]
    errors: list[ErrorInfo] = None

    def serialize(self):
        payload = {
            "msg": self.msg,
            "location": self.location,
        }
        if self.errors:
            payload["errors"] = [str(err) for err in self.errors]
        return payload


def format_errors(errors: list[ErrorWrapper]):
    for error in errors:
        location = ".".join(error.loc_tuple())
        error = error.exc
        if isinstance(error, ValidationError):
            errors = [
                ErrorInfo(err["msg"], err["type"], ".".join(err["loc"]))
                for err in error.errors()
            ]
            yield ResolveError("ValidatorError", location, errors)
        elif isinstance(error, (PydanticTypeError, PydanticValueError)):
            yield ResolveError(str(error), location)
        elif isinstance(error, TypeError):
            yield ResolveError("Problem with init", location)


class RequestValidationError(HTTPException):
    def __init__(self, errors: list[ResolveError]):
        super().__init__(status_code=422, detail="")
        self.errors = errors

    def serialize(self):
        data = super().serialize()
        data["error"]["errors"] = [err.serialize() for err in self.errors]
        return data
