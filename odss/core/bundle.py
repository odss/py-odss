import typing as t

from .events import ServiceEvent


class IBundle:

    UNINSTALLED = 1
    INSTALLED = 2
    RESOLVED = 4
    STARTING = 8
    STOPPING = 16
    ACTIVE = 32

    @property
    def id(self) -> str:
        pass

    @property
    def state(self) -> int:
        pass

    @property
    def name(self) -> str:
        pass

    def get_module(self) -> object:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class IBundleContext:
    def get_bundle(self, bundle_id: int = None) -> IBundle:
        pass

    def get_bundles(self) -> t.Iterable[IBundle]:
        pass

    def get_property(self, name: str) -> str:
        pass

    def get_service(self, reference) -> t.Any:
        pass

    def unget_service(self, reference) -> None:
        pass

    def get_service_reference(self, clazz, filter=None):
        pass

    def get_service_references(self, clazz, filter=None):
        pass

    async def install_bundle(self, name, path=None):
        pass

    async def register_service(self, clazz, service, properties=None):
        pass

    def add_framework_listener(self, listener):
        pass

    def add_bundle_listener(self, listener):
        pass

    def add_service_listener(self, listener, interface=None, filter=None):
        pass

    def remove_framework_listener(self, listener):
        pass

    def remove_bundle_listener(self, listener):
        pass

    def remove_service_listener(self, listener):
        pass

    async def __fire_service_event(self, kind, reference):
        pass


class Bundle(IBundle):
    def __init__(self, framework, bundle_id, name, integration):
        self.__framework = framework
        self.__id = bundle_id
        self.__name = name
        self.__integration = integration
        self.__state = Bundle.RESOLVED
        self.__context = None

    @property
    def id(self):
        return self.__id

    @property
    def state(self):
        return self.__state

    @property
    def name(self):
        return self.__name

    @property
    def version(self):
        return "0.0.0"

    def get_location(self):
        return getattr(self.__integration.module, "__file__", "")

    def get_module(self):
        return self.__integration.module

    async def start(self):
        await self.__framework.start_bundle(self)

    async def stop(self):
        await self.__framework.stop_bundle(self)

    async def uninstall(self):
        await self.__framework.uninstall_bundle(self)

    def set_context(self, context):
        self.__context = context

    def get_context(self):
        return self.__context

    def remove_context(self):
        self.__context = None

    def __str__(self):
        """
        String representation
        """
        return "Bundle(id={0}, name={1})".format(self.__id, self.__name)

    def _set_state(self, state):
        self.__state = state

    def get_references(self):
        return self.__framework.get_bundle_references(self)

    def get_using_services(self):
        return self.__framework.get_bundle_using_services(self)


class BundleContext:
    def __init__(self, framework, bundle, events):
        self.__framework = framework
        self.__bundle = bundle
        self.__events = events

    def __str__(self):
        return "BundleContext({0})".format(self.__bundle)

    def get_framework(self):
        return self.__framework

    def get_bundle(self, bundle_id=None) -> Bundle:
        return self.__framework.get_bundle_by_id(bundle_id)

    def get_bundles(self):
        return self.__framework.get_bundles()

    def get_property(self, name: str):
        return self.__framework.get_property(name)

    def get_service(self, reference):
        return self.__framework.get_service(self.__bundle, reference)

    def unget_service(self, reference):
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

    async def __fire_service_event(self, kind, reference):
        event = ServiceEvent(kind, reference)
        await self.__events.fire_service_event(event)
