class Bundle:

    UNINSTALLED = 1
    INSTALLED = 2
    RESOLVED = 4
    STARTING = 8
    STOPPING = 16
    ACTIVE = 32

    def __init__(self, framework, bundle_id, bundle_name, py_module):
        self.__framework = framework
        self.__id = bundle_id
        self.__name = bundle_name
        self.__module = py_module
        self._state = Bundle.RESOLVED

    @property
    def framework(self):
        return self.__framework

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    def state(self):
        return self._state

    @property
    def module(self):
        return self.__module


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
