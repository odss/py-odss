import abc
import asyncio
import dataclasses as dc
import inspect
import re
import typing as t
from collections import namedtuple

from odss.http.common import (
    UnprocessableContentError,
    JsonError,
    Request,
    RouteInfo,
    decode_json,
)
from pydantic import BaseModel, TypeAdapter, ValidationError, dataclasses as pdc

sequence_types = (list, set, tuple)


class SystemFieldType:
    REQUEST = "request"
    ROUTE_INFO = "route-info"


@dc.dataclass
class SystemField:
    kind: SystemFieldType
    name: str


@dc.dataclass
class IncjectContext:
    request: Request
    route: RouteInfo
    values: list[t.Any] = dc.field(default_factory=dict)


class Resolver(metaclass=abc.ABCMeta):
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

    @abc.abstractmethod
    def resolve(self, context: IncjectContext):
        pass


class RequestResolver(Resolver):
    def resolve(self, context: IncjectContext):
        return {self.name: context.request}


class RouteResolver(Resolver):
    def resolve(self, context: IncjectContext):
        return {self.name: context.request}


class ModelResolver(Resolver):
    def __init__(self, name: str, model: BaseModel):
        super().__init__(name)
        self.model = model

    def resolve(self, context: IncjectContext):
        return {self.name: context.model}


class BodyResolver(Resolver):
    def __init__(self, name, model: BaseModel):
        super().__init__(name)
        self.model = model if not dc.is_dataclass(model) else pdc.dataclass(model)

    async def resolve(self, context: IncjectContext):
        request = context.request
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            value = None
            if request.content_type == "application/json":
                data = await request.read()
                value = decode_json(data)
            elif "multipart/form-data" in request.content_type:
                value = await request.post()
            if value:
                obj = self.model(**value)
                return {self.name: obj}
        return {}


class FieldResolver(Resolver):
    def __init__(self, name, field):
        super().__init__(name)
        self.field = field

    def resolve(self, context: IncjectContext):
        values = {}
        type_adapter, default_value, required = self.field
        is_list = type_adapter.core_schema["type"] == "list"

        value = self.get_value(context, self.name, default_value, is_list)
        valid_value = type_adapter.validate_python(value)
        values.update({self.name: valid_value})
        return values

    @abc.abstractmethod
    def get_value(self, context: IncjectContext, field):
        pass


class QueryResolver(FieldResolver):
    def get_value(self, context: IncjectContext, name: str, default_value, is_list):
        query = context.request.query
        if is_list:
            return query.getall(name)
        return query.get(name, default_value)


class ParamResolver(FieldResolver):
    def get_value(self, context: IncjectContext, name: str, default_value, is_list):
        return context.request.match_info.get(name, default_value)


# class QueryModel(BaseModel):
#     pass


# class BodyModel(BaseModel):
#     pass


# class ParamsModel(BaseModel):
#     pass


@dc.dataclass
class Dependency:
    fields: list[Resolver] = dc.field(default_factory=list)
    return_field: t.Any = None


def get_dependency(path, handler: t.Callable) -> Dependency:
    path_param_names = set(re.findall("{(.*?)}", path))
    handler_signature = inspect.signature(handler)
    fields = []
    has_body = False

    for name, spec in handler_signature.parameters.items():
        annotation = spec.annotation
        if annotation == spec.empty:
            raise RuntimeError(f"The parameter {name} must have annotation")

        if check_system_field(fields, spec):
            continue

        default_value = None
        required = True
        if spec.default != spec.empty:
            default_value = spec.default
            required = False

        field = (TypeAdapter(annotation), default_value, required)
        if name in path_param_names:
            fields.append(ParamResolver(name, field))
        elif has_body is not None and is_body_field(annotation):
            has_body = True
            fields.append(BodyResolver(name, spec.annotation))
        else:
            fields.append(QueryResolver(name, field))

    return_field = (
        handler_signature.return_annotation
        if handler_signature.return_annotation != inspect._empty
        else None
    )
    return Dependency(fields=fields, return_field=return_field)


def check_system_field(deps: list[t.Any], param: inspect.Parameter) -> bool:
    if param.annotation == Request:
        deps.append(RequestResolver(param.name))
        return True
    elif param.annotation == RouteInfo:
        deps.append(RouteResolver(param.name))
        return True
    return False


def is_body_field(annotation) -> bool:
    if is_pydantic_base_model(annotation) or dc.is_dataclass(annotation):
        return True


def is_pydantic_base_model(obj):
    try:
        return issubclass(obj, BaseModel)
    except TypeError:
        return False


async def resolve_dependency(
    deps: Dependency, request: Request, props
) -> dict[str, t.Any]:
    all_errors = []
    context = IncjectContext(request=request, route=props)
    values = {}
    for field in deps.fields:
        try:
            valid_values = field.resolve(context)
            if asyncio.iscoroutine(valid_values):
                valid_values = await valid_values
            values.update(valid_values)
        except ValidationError as error:
            all_errors.append(format_error(error, field.name))
        except JsonError as ex:
            raise UnprocessableContentError() from ex
        if all_errors:
            raise RequestValidationError(all_errors)
    return values


ErrorInfo = namedtuple("ValidInfo", "msg,type,location")


@dc.dataclass
class ResolveError:
    msg: str
    location: tuple[str]
    errors: list[ErrorInfo] = None

    def to_json(self):
        payload = {
            "msg": self.msg,
            "location": self.location,
        }
        if self.errors:
            payload["errors"] = [str(err) for err in self.errors]
        return payload


def format_error(error: ValidationError, location: str):
    errors = [
        ErrorInfo(err["msg"], err["type"], ".".join(err["loc"]))
        for err in error.errors()
    ]
    return ResolveError(msg="ValidatorError", location=location, errors=errors)


class RequestValidationError(UnprocessableContentError):
    def __init__(self, errors: list[ResolveError]):
        super().__init__()
        self.errors = errors

    def to_json(self):
        data = super().to_json()
        data["errors"] = [err.to_json() for err in self.errors]
        return data
