from .errors import BundleException
from .events import ServiceEvent


class Bundle:

    UNINSTALLED = 1
    INSTALLED = 2
    RESOLVED = 4
    STARTING = 8
    STOPPING = 16
    ACTIVE = 32

    def __init__(self, framework, bundle_id, name, py_module):
        self.__framework = framework
        self.__id = bundle_id
        self.__name = name
        self.__module = py_module
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

    def get_module(self):
        return self.__module

    async def start(self):
        await self.__framework.start_bundle(self)

    async def stop(self):
        await self.__framework.stop_bundle(self)

    def set_context(self, context):
        self.__context = context

    def get_context(self):
        return self.__context

    def remove_context(self):
        self.__context = None

    def __str__(self):
        '''
        String representation
        '''
        return "Bundle(id={0}, name={1})".format(self.__id, self.__name)

    def _set_state(self, state):
        self.__state = state


class BundleContext:

    def __init__(self, framework, bundle, registry, events):
        self.__framework = framework
        self.__bundle = bundle
        self.__events = events
        self.__registry = registry

    def __str__(self):
        return "BundleContext({0})".format(self.__bundle)

    def get_bundle(self, bundle_id=None) -> Bundle:
        return self.__framework.get_bundle_by_id(bundle_id)

    @property
    def bundles(self):
        return self.__framework.bundles

    def get_property(self, name: str):
        return self.__framework.get_property(name)

    def get_service(self, reference):
        return self.__registry.get_service(self.__bundle, reference)

    def unget_service(self, reference):
        return self.__registry.unget_service(self.__bundle, reference)

    def get_service_reference(self, clazz, filter=None):
        return self.__registry.find_service_reference(clazz, filter)

    def get_service_references(self, clazz, filter=None):
        return self.__registry.find_service_references(clazz, filter)

    async def install_bundle(self, name, path=None):
        return await self.__framework.install_bundle(name, path)

    async def register_service(self, clazz, service, properties=None):
        if clazz is None:
            raise BundleException('Invalid registration parameter: clazz')
        if service is None:
            raise BundleException('Invalid registration parameter: service')

        properties = properties.copy() if isinstance(properties, dict) else {}

        registration = self.__registry.register(
            self.__bundle, clazz, service, properties)
        
        await self.__fire_service_event(
            ServiceEvent.REGISTERED, registration.get_reference()
        )
        return registration

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
