import inspect
import functools
import logging
import types
import typing as t

from .consts import (
    HANDLER_PROVIDES,
    HANDLER_REQUIRES,
    METHOD_CALLBACK,
    CALLBACK_VALIDATE,
    CALLBACK_INVALIDATE,
)
from .contexts import get_factory_context


TClass = t.TypeVar("TClass")


def _only_classes(self, clazz: TClass) -> None:
    if not inspect.isclass(clazz):
        parent = (type(self).__name__,)
        name = (type(clazz).__name__,)
        msg = f"@{parent} can decorate only classes, not '{name}'"
        raise TypeError(msg)


def _get_specification(specification):
    if not specification or specification is object:
        raise ValueError("No specifications given")
    elif inspect.isclass(specification):
        return "{0}.{1}".format(specification.__module__, specification.__qualname__)
    elif isinstance(specification, str):
        return specification
    raise ValueError("Unknow specifications type: {}".format(type(specification)))


def _get_specifications(specifications):
    if isinstance(specifications, (list, tuple)):
        return [_get_specification(specification) for specification in specifications]
    return [_get_specification(specifications)]


def _get_init_spec(clazz: TClass):
    init = getattr(clazz, "__init__", None)
    if init:
        sig = inspect.signature(init)
        for pname, pvalue in sig.parameters.items():
            if pname != "self" and pvalue.annotation != sig.empty:
                yield _get_specification(pvalue.annotation)


def _set_method_callback(method, kind):
    setattr(method, METHOD_CALLBACK, kind)


def _setup_callbacks(factory_context, clazz):
    methods = inspect.getmembers(clazz, inspect.isroutine)
    for _, method in methods:
        if hasattr(method, METHOD_CALLBACK):
            kind = getattr(method, METHOD_CALLBACK)
            factory_context.set_callback(kind, method)


def Component(name):
    if not name:
        raise TypeError("Expected 'name'")

    def prepare_factory_context(clazz, name):
        factory_context = get_factory_context(clazz)
        if not factory_context.completed:
            factory_context.name = name
            if not factory_context.has_handler(HANDLER_REQUIRES):
                requires = list(_get_init_spec(clazz))
                if len(requires):
                    factory_context.set_handler(HANDLER_REQUIRES, requires)
            _setup_callbacks(factory_context, clazz)
            factory_context.completed = True
        else:
            raise TypeError("component has already been prepared")

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
        requires = _get_specifications(specifications)
        get_factory_context(clazz).set_handler(HANDLER_REQUIRES, requires)
        return clazz

    return requires_decorator


def Instantiate(name, properties=None):
    if inspect.isclass(name):
        clazz = name
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
        specs = _get_specifications(specifications)
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


def Bind(method):
    print("Bind")
    return method


def Unbind(method):
    print("Unbind")
    return method


def Validate(*args):
    if not len(args):
        raise TypeError("Missing args")
    if len(args) == 1:
        if inspect.isroutine(args[0]):
            _set_method_callback(args[0], CALLBACK_VALIDATE)
            return args[0]

    def ValidateDecorator(method):
        _set_method_callback(method, CALLBACK_VALIDATE)
        return method

    return ValidateDecorator


def Invalidate(*args):
    if not len(args):
        raise TypeError("Missing args")
    if len(args) == 1:
        if inspect.isroutine(args[0]):
            _set_method_callback(args[0], CALLBACK_INVALIDATE)
            return args[0]

    def InvalidateDecorator(method):
        _set_method_callback(method, CALLBACK_INVALIDATE)
        return method

    return InvalidateDecorator


if __name__ == "__main__":

    class IManager:
        pass

    class IService:
        pass

    class IListener:
        pass

    class IBundleContext:
        pass

    @Component
    @Provides([IManager])
    class Test:
        def __init__(self, s: IService) -> None:
            pass

        @Bind
        def add_listener(self, listener: IListener) -> None:
            pass

        @Unbind
        def remove_listener(self, listener: IListener):
            pass

        @Validate(1, 2, 3)
        def valid(self, ctx: IBundleContext):
            pass

        @Invalidate
        def invalid(self, ctx: IBundleContext):
            pass

    test = Test(1)
    test.valid(2)
