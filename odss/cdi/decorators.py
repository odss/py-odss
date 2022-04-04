import inspect
import typing as t

from odss.core.utils import classes_name

from .consts import (
    CALLBACK_BIND,
    CALLBACK_INVALIDATE,
    CALLBACK_UNBIND,
    CALLBACK_VALIDATE,
    HANDLER_PROVIDES,
    HANDLER_REQUIRES,
    METHOD_CALLBACK,
)
from .contexts import get_factory_context, prepare_factory_context

TClass = t.TypeVar("TClass")


def _only_classes(self, clazz: TClass) -> None:
    if not inspect.isclass(clazz):
        parent = (type(self).__name__,)
        name = (type(clazz).__name__,)
        msg = f"@{parent} can decorate only classes, not '{name}'"
        raise TypeError(msg)


def component(name):
    if not name:
        raise TypeError("Expected 'name'")

    if inspect.isclass(name) or inspect.isroutine(name):
        prepare_factory_context(name, "{}.{}".format(name.__module__, name.__name__))
        return name

    if not name:
        raise ValueError("Invalid component name '{0}'".format(name))

    def component_decorator(clazz):
        if not inspect.isclass(clazz) and not inspect.isroutine(clazz):
            raise TypeError("Class exptected, got '{0}'".format(type(clazz).__name__))
        prepare_factory_context(clazz, name)
        return clazz

    return component_decorator


def instantiate(name, properties=None):
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


def provides(specifications):
    """
    The ``@Provides`` decorator defines a service to expose

    :Example:

    .. code-block:: python

        @Component()
        @provides  # provide "Foo"
        class Foo:
            pass

        @provides  # provide "IFoo"
        class Foo(IFoo):
            pass


        @Component()
        @provides("Foo")  # provide "Foo"
        class Foo:
            pass
    """

    def provides_decorator(clazz):
        nonlocal specifications
        if not specifications:
            specifications = clazz.__bases__
        specs = classes_name(specifications)
        filtered_specs = []
        for spec in specs:
            if spec not in filtered_specs:
                filtered_specs.append(spec)

        get_factory_context(clazz).set_handler(HANDLER_PROVIDES, filtered_specs)
        return clazz

    return provides_decorator


def requires(field, specifications, query = None):
    if not field:
        raise ValueError("Empty field name")
    if not isinstance(field, str):
        raise TypeError("Field name must be a string")

    def requires_decorator(clazz):
        specs = classes_name(specifications)
        fields = get_factory_context(clazz).set_default_handler(HANDLER_REQUIRES, {})
        fields[field] = (specs, query)

        setattr(clazz, field, None)

        return clazz

    return requires_decorator


def property(field, name, value=None):
    def propert_decorator(method):
        return method

    return propert_decorator


def bind(specification=None, spec_filter=None, reference=False):
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


def unbind(specification=None, spec_filter=None, reference=False):
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


def validate(*args):
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


def invalidate(*args):
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
