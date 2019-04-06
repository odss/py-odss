import copy
import typing as t

from odss.core.bundle import Bundle, BundleContext

from . import consts


TClass = t.TypeVar("TClass")


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
            return copy.deepcopy(self.__instances)
        return {self.name: {}}

    def has_handler(self, name: str) -> bool:
        return name in self.__handlers

    def set_handler(self, name: str, args: any) -> None:
        self.__handlers[name] = args

    def get_handler(self, name: str) -> any:
        return self.__handlers.get(name)

    def get_handlers_names(self) -> t.Iterable[str]:
        return tuple(self.__handlers.keys())

    def get_handlers(self) -> t.Iterable[t.Tuple[str, any]]:
        return self.__handlers.items()

    def has_callback(self, kind):
        return kind in self._callbacks

    def set_callback(self, kind, method):
        self._callbacks[kind] = method

    def get_callback(self, kind):
        return self._callbacks[kind]


class ComponentContext:
    def __init__(
        self,
        name: str,
        factory_class: t.Callable,
        factory_context: FactoryContext,
        properties: dict,
    ) -> None:
        self.name = name
        self.factory_class = factory_class
        self.factory_context = factory_context
        self.properties = properties

    def get_bundle(self):
        return self.factory_context.get_bundle()

    def get_bundle_context(self):
        return self.factory_context.get_bundle_context()


def is_component_factory(clazz: TClass) -> bool:
    return hasattr(clazz, consts.ODSS_FACTORY_CONTEXT)


def get_factory_context(clazz: TClass) -> FactoryContext:
    factory_context: FactoryContext = getattr(clazz, consts.ODSS_FACTORY_CONTEXT, None)
    if factory_context is None:
        factory_context = FactoryContext()
        setattr(clazz, consts.ODSS_FACTORY_CONTEXT, factory_context)
    return factory_context
