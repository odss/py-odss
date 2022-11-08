import collections
import inspect
import typing as t

from odss.core.bundle import Bundle, BundleContext
from odss.core.utils import class_name

from . import consts

TClass = t.TypeVar("TClass")


class Requirement:
    def __init__(self, specification, spec_filter="", reference=False):
        self.specification = specification
        self.spec_filter = spec_filter
        self.reference = reference

    def __eq__(self, other):
        if other is self:
            return True

        if not isinstance(other, Requirement):
            return False

        if self.specification != other.specification:
            return False

        if self.spec_filter != other.spec_filter:
            return False

        return True

    def __hash__(self):
        return id(self.specification + self.spec_filter + str(self.reference))


def prepare_requirement(method, args):
    if args:
        return Requirement(*args)
    specification = list(get_method_spec(method))[0]
    return Requirement(specification)


def _get_init_spec(clazz: TClass):
    init_method = getattr(clazz, "__init__", None)
    if init_method:
        yield from get_method_spec(init_method)


def get_method_spec(method: t.Callable):
    sig = inspect.signature(method)
    for pname, pvalue in sig.parameters.items():
        if pname != "self" and pvalue.annotation != sig.empty:
            yield class_name(pvalue.annotation)


def _setup_callbacks(factory_context, clazz):
    methods = inspect.getmembers(clazz, inspect.isroutine)
    binds = collections.defaultdict(dict)
    for _, method in methods:
        if hasattr(method, consts.METHOD_CALLBACK):
            kind, args = getattr(method, consts.METHOD_CALLBACK)
            if kind == consts.CALLBACK_BIND or kind == consts.CALLBACK_UNBIND:
                requirement = prepare_requirement(method, args)
                binds[requirement][kind] = method
            else:
                factory_context.set_callback(kind, method, args)
    if binds:
        for requirement, bind in binds.items():
            factory_context.append_handler(consts.HANDLER_BIND, (requirement, bind))


def prepare_factory_context(clazz, name):
    factory_context = get_factory_context(clazz)
    if not factory_context.completed:
        factory_context.name = name
        requires = tuple(_get_init_spec(clazz))
        if requires:
            factory_context.set_handler(consts.HANDLER_CONSTRUCTOR_REQUIRES, requires)
        _setup_callbacks(factory_context, clazz)
        factory_context.completed = True
    else:
        raise TypeError("Component has already been prepared")


class FactoryContext:
    def __init__(self):
        self.name = ""
        self.completed = False
        self.__instances = {}
        self.__handlers = {}
        self._callbacks = {}
        self.__bundle = None

    def set_bundle(self, bundle: Bundle):
        self.__bundle = bundle

    def get_bundle(self) -> Bundle:
        return self.__bundle

    def get_bundle_context(self) -> BundleContext:
        return self.__bundle.get_context()

    def has_instance(self, name: str) -> bool:
        return name in self.__instances

    def add_instance(self, name: str, properties: dict = None):
        if name in self.__instances:
            raise NameError(name)
        if properties is None:
            properties = {}
        self.__instances[name] = properties

    def get_instances(self) -> t.Dict:
        if self.__instances:
            return tuple(self.__instances.items())
        return ((self.name, {}),)

    def has_handler(self, name: str) -> bool:
        return name in self.__handlers

    def set_handler(self, name: str, args: any) -> None:
        if name in self.__handlers:
            raise ValueError(f"Handler {name} already register")
        self.__handlers[name] = args

    def set_default_handler(self, name: str, args: any) -> any:
        if name not in self.__handlers:
            self.__handlers[name] = args
        return self.__handlers[name]

    def append_handler(self, name, args: any) -> None:
        if name not in self.__handlers:
            self.__handlers[name] = []
        self.__handlers[name].append(args)

    def get_handler(self, name: str) -> any:
        return self.__handlers.get(name)

    def get_handlers_names(self) -> t.Iterable[str]:
        return tuple(self.__handlers.keys())

    def get_handlers(self) -> t.Iterable[t.Tuple[str, any]]:
        return self.__handlers.items()

    def set_callback(self, kind: str, method: t.Callable, args: t.Any):
        self._callbacks[kind] = (method, args)

    def get_callback(self, kind: str):
        return self._callbacks.get(kind, (None, None))


class ComponentContext:
    def __init__(
        self,
        name: str,
        factory_target: t.Callable,
        factory_context: FactoryContext,
        properties: dict,
    ) -> None:
        self.name = name
        self.factory_target = factory_target
        self.factory_context = factory_context
        self.properties = properties

    def get_bundle(self) -> Bundle:
        return self.factory_context.get_bundle()

    def get_bundle_context(self) -> BundleContext:
        return self.factory_context.get_bundle_context()

    def get_callback(self, kind: str) -> t.Tuple[t.Callable, t.Any]:
        return self.factory_context.get_callback(kind)


def has_factory_context(target: TClass) -> bool:
    return hasattr(target, consts.ODSS_FACTORY_CONTEXT)


def get_factory_context(target: TClass) -> FactoryContext:
    factory_context: FactoryContext = getattr(target, consts.ODSS_FACTORY_CONTEXT, None)
    if factory_context is None:
        factory_context = FactoryContext()
        setattr(target, consts.ODSS_FACTORY_CONTEXT, factory_context)
    return factory_context
