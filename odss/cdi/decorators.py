import inspect
import typing as t

from odss.core.utils import classes_name

from .consts import (
    HANDLER_PROVIDES,
    HANDLER_REQUIRES,
    METHOD_CALLBACK,
    CALLBACK_VALIDATE,
    CALLBACK_INVALIDATE,
    CALLBACK_BIND,
    CALLBACK_UNBIND,
)
from .contexts import get_factory_context, prepare_factory_context


TClass = t.TypeVar("TClass")


def _only_classes(self, clazz: TClass) -> None:
    if not inspect.isclass(clazz):
        parent = (type(self).__name__,)
        name = (type(clazz).__name__,)
        msg = f"@{parent} can decorate only classes, not '{name}'"
        raise TypeError(msg)


def Component(name):
    if not name:
        raise TypeError("Expected 'name'")

    if inspect.isclass(name):
        prepare_factory_context(name, "{}.{}".format(name.__module__, name.__name__))
        return name

    if not name:
        raise ValueError("Invalid component name '{0}'".format(name))

    def component_decorator(clazz):
        if not inspect.isclass(clazz):
            raise TypeError("Class exptected, got '{0}'".format(type(clazz).__name__))
        prepare_factory_context(clazz, name)
        return clazz

    return component_decorator


def Requires(*specifications):
    def requires_decorator(clazz):
        requires = classes_name(specifications)
        get_factory_context(clazz).set_handler(HANDLER_REQUIRES, requires)
        return clazz

    return requires_decorator


def Instantiate(name, properties=None):
    if inspect.isclass(name):
        get_factory_context(name).add_instance(name.__name__)
        return name

    if not isinstance(name, str):
        raise TypeError("Instance name must be a string")

    name = name.strip()
    if not name:
        raise ValueError("Invalid instance name '{0}'".format(name))

    if properties is not None and not isinstance(properties, dict):
        raise TypeError("Instance properties must be a dictionary")

    def instantiate_decorator(clazz):
        if not inspect.isclass(clazz):
            raise TypeError("Class exptected, got '{0}'".format(type(clazz).__name__))
        get_factory_context(clazz).add_instance(name, properties)
        return clazz

    return instantiate_decorator


def Provides(specifications):
    def provides_decorator(clazz):
        nonlocal specifications
        if not specifications:
            specifications = clazz.__bases__
        specs = classes_name(specifications)
        filtered_specs = []
        for spec in specs:
            if spec not in filtered_specs:
                filtered_specs.append(spec)
        config = get_factory_context(clazz)
        config.set_handler(HANDLER_PROVIDES, filtered_specs)
        return clazz

    return provides_decorator


def Property(field, name, value=None):
    print("Property")

    def propert_decorator(method):
        return method

    return propert_decorator


def Bind(specification=None, spec_filter=None, reference=False):
    if inspect.isroutine(specification):
        setattr(specification, METHOD_CALLBACK, (CALLBACK_BIND, None))
        return specification

    def BindDecorator(method):
        setattr(
            method,
            METHOD_CALLBACK,
            (CALLBACK_BIND, (specification, spec_filter, reference)),
        )
        return method

    return BindDecorator


def Unbind(specification=None, spec_filter=None, reference=False):
    if inspect.isroutine(specification):
        setattr(specification, METHOD_CALLBACK, (CALLBACK_UNBIND, None))
        return specification

    def UnbindDecorator(method):
        setattr(
            method,
            METHOD_CALLBACK,
            (CALLBACK_UNBIND, (specification, spec_filter, reference)),
        )
        return method

    return UnbindDecorator


def Validate(*args):
    if not len(args):
        raise TypeError("Missing args")
    if len(args) == 1:
        if inspect.isroutine(args[0]):
            setattr(args[0], METHOD_CALLBACK, (CALLBACK_VALIDATE, None))
            return args[0]

    def ValidateDecorator(method):
        setattr(method, METHOD_CALLBACK, (CALLBACK_VALIDATE, args))
        return method

    return ValidateDecorator


def Invalidate(*args):
    if not len(args):
        raise TypeError("Missing args")
    if len(args) == 1:
        if inspect.isroutine(args[0]):
            setattr(args[0], METHOD_CALLBACK, (CALLBACK_INVALIDATE, None))
            return args[0]

    def InvalidateDecorator(method):
        setattr(method, METHOD_CALLBACK, (CALLBACK_INVALIDATE, args))
        return method

    return InvalidateDecorator