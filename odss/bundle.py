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
    
    def start(self):
        self.__framework.start_bundle(self)

    def stop(self):
        self.__framework.stop_bundle(self)

    def __str__(self):
        '''
        String representation
        '''
        return "Bundle(id={0}, name={1})".format(self.__id, self.__name)

    def _set_state(self, state):
        self.__state = state

class BundleContext:

    def __init__(self, framework, bundle):
        self.__framework = framework
        self.__bundle = bundle

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
