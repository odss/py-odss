import typing as t

class IBundle:

    UNINSTALLED = 1
    INSTALLED = 2
    RESOLVED = 4
    STARTING = 8
    STOPPING = 16
    ACTIVE = 32

    @property
    def id(self) -> str:
        """
        Return the bundle ID
        """

    @property
    def state(self) -> int:
        """
        Return the bundle state
        """

    @property
    def name(self) -> str:
        """
        Return the bundle name
        """

    def get_module(self) -> object:
        """
        Return the bundle python module
        """

    async def start(self) -> None:
        """
        Start bundle
        """

    async def stop(self) -> None:
        """
        Stop bundle
        """


class IBundleContext:
    def get_bundle(self, bundle_id: int = None) -> IBundle:
        """
        Return bundle by bundle id or bundle assign to current context
        """

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

    def register_service(self, clazz, service, properties=None):
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

    # def __fire_service_event(self, kind, reference):
    #     pass


