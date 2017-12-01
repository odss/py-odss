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

    @property
    def module(self):
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

    def __init__(self, framework, bundle, events):
        self.__framework = framework
        self.__bundle = bundle
        self.__events = events

    def __str__(self):
        return "BundleContext({0})".format(self.__bundle)

    def get_bundle(self, bundle_id=None) -> Bundle:
        pass

    @property
    def bundles(self):
        return self.__framework.bundles

    def get_property(self, name: str):
        return self.__framework.get_property(name)

    def get_service(self, reference):
        pass

    def get_service_reference(self, clazz, filter=None):
        return self.__framework.get_service_reference(clazz, filter)

    def get_service_references(self, clazz, filter=None):
        return self.__framework.get_service_references(clazz, filter)

    def install_bundle(self, name, path=None):
        pass

    def install_package(self, path, recursive=False):
        pass

    def register_service(self, clazz, service, properties=None):
        return self.__framework.register_service(
            self.__bundle, clazz, service, properties)

    def add_bundle_listener(self, listener):
        return self.__events.add_bundle_listener(listener)

    def add_framework_listener(self, listener):
        return self.__events.add_framework_listener(listener)

    def add_service_listener(self, listener, interface=None, query_filter=None):
        return self.__events.add_service_listener(listener, interface, query_filter)
    
    def remove_bundle_listener(self, listener):
        return self.__events.remove_listener(listener)

    def remove_framework_listener(self, listener):
        return self.__events.remove_listener(listener)
    
    def remove_service_listener(self, listener):
        return self.__events.remove_listener(listener)