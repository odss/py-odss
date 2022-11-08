import abc
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


class IServiceReference(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_bundle(self) -> IBundle:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_property(self, name: str) -> t.Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_properties(self) -> t.Any:
        raise NotImplementedError()


class IBundleContext:
    def get_bundle(self, bundle_id: int = None) -> IBundle:
        """
        Return bundle by bundle id or bundle assign to current context
        """

    def get_bundles(self) -> list[IBundle]:
        pass

    def get_property(self, name: str) -> str:
        pass

    def get_service(self, reference: IServiceReference) -> t.Any:
        pass

    def unget_service(self, reference: IServiceReference) -> None:
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


class IServiceTrackerListener(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def on_adding_service(self, reference, service):
        raise NotImplementedError()

    @abc.abstractmethod
    async def on_modified_service(self, reference, service):
        raise NotImplementedError()

    @abc.abstractmethod
    async def on_removed_service(self, reference, service):
        raise NotImplementedError()
