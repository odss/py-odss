import typing as t
from odss.common import IBundle, IBundleContext


class Bundle(IBundle):
    __slots__ = [
        "__framework",
        "__id",
        "__name",
        "__integration",
        "__state",
        "__context",
        "_start_level",
    ]

    def __init__(self, framework, bundle_id, name, integration):
        self.__framework = framework
        self.__id = bundle_id
        self.__name = name
        self.__integration = integration
        self.__state = Bundle.RESOLVED
        self.__context = None
        self._start_level = None

    @property
    def id(self):
        """
        Return the bundle ID
        """
        return self.__id

    @property
    def state(self):
        """
        Return bundle state
        """
        return self.__state

    @property
    def name(self):
        """
        Return bundle name
        """
        return self.__name

    @property
    def start_level(self):
        return self._start_level

    @start_level.setter
    def start_level(self, level: int):
        if level < 1:
            raise ValueError("Start level must be greater than zero.")
        self._start_level = level

    @property
    def version(self):
        """
        Return bundle version"
        """
        return getattr(self.__integration.module, "__version__", "0.0.0")

    def get_location(self):
        """
        Return bundle location
        """
        return getattr(self.__integration.module, "__file__", "")

    def get_module(self):
        """
        Return bundle python module
        """
        return self.__integration.module

    async def start(self):
        """
        Start bundle
        """
        await self.__framework.start_bundle(self)

    async def stop(self):
        """
        Stop bundle
        """
        await self.__framework.stop_bundle(self)

    async def uninstall(self) -> None:
        await self.__framework.uninstall_bundle(self)

    def set_context(self, context: IBundleContext) -> None:
        self.__context = context

    def get_context(self) -> IBundleContext:
        return self.__context

    def remove_context(self) -> None:
        self.__context = None

    def __str__(self) -> str:
        """
        String representation
        """
        return "Bundle(id={0}, name={1})".format(self.__id, self.__name)

    def _set_state(self, state) -> None:
        self.__state = state

    def get_references(self):
        return self.__framework.get_bundle_references(self)

    def get_using_services(self):
        return self.__framework.get_bundle_using_services(self)


class BundleContext(IBundleContext):
    def __init__(self, framework, bundle, events):
        self.__framework = framework
        self.__bundle = bundle
        self.__events = events

    def __str__(self):
        return "BundleContext({0})".format(self.__bundle)

    def get_framework(self):
        return self.__framework

    def get_bundle(self):
        return self.__bundle

    def get_bundle_by_id(self, bundle_id: int) -> IBundle:
        return self.__framework.get_bundle_by_id(bundle_id)

    def get_bundles(self) -> list[IBundle]:
        return self.__framework.get_bundles()

    def get_property(self, name: str, defaults: t.Any | None = None):
        return self.__framework.get_property(name, defaults)

    def get_service(self, reference):
        return self.__framework.get_service(self.__bundle, reference)

    def unget_service(self, reference):
        """
        Disables a reference to the service
        """
        return self.__framework.unget_service(self.__bundle, reference)

    def get_service_reference(self, clazz=None, filter=None):
        return self.__framework.find_service_reference(clazz, filter)

    def get_service_references(self, clazz=None, filter=None):
        return self.__framework.find_service_references(clazz, filter)

    def get_bundle_references(self, bundle):
        return self.__framework.get_bundle_references(bundle)

    def get_bundle_imported_services(self, bundle):
        return self.__framework.get_bundle_imported_services(bundle)

    async def install_bundle(self, name, path=None):
        return await self.__framework.install_bundle(name, path)

    async def register_service(self, clazz, service, properties=None):
        return await self.__framework.register_service(
            self.__bundle, clazz, service, properties
        )

    def add_framework_listener(self, listener):
        return self.__events.framework.add_listener(listener)

    def add_bundle_listener(self, listener):
        return self.__events.bundles.add_listener(listener)

    def add_service_listener(self, listener, interface=None, filter=None):
        return self.__events.services.add_listener(listener, interface, filter)

    def remove_framework_listener(self, listener):
        return self.__events.framework.remove_listener(listener)

    def remove_bundle_listener(self, listener):
        return self.__events.bundles.remove_listener(listener)

    def remove_service_listener(self, listener):
        return self.__events.services.remove_listener(listener)
