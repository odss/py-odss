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
    @abc.abstractmethod
    def id(self) -> str:
        """
        Return the bundle ID
        """

    @property
    @abc.abstractmethod
    def state(self) -> int:
        """
        Return the bundle state
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Return the bundle name
        """

    @property
    @abc.abstractmethod
    def start_level(self) -> int:
        ...

    @abc.abstractmethod
    def get_module(self) -> object:
        """
        Return the bundle python module
        """

    @abc.abstractmethod
    async def start(self) -> None:
        """
        Start bundle
        """

    @abc.abstractmethod
    async def stop(self) -> None:
        """
        Stop bundle
        """


class IServiceReference(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_id(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_bundle(self) -> IBundle:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_property(self, name: str, default: t.Any | None = None) -> t.Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_properties(self) -> t.Any:
        raise NotImplementedError()


class IBundleContext:
    @abc.abstractmethod
    def get_bundle(self) -> IBundle:
        """
        Return context bundle
        """

    @abc.abstractmethod
    def get_bundle_by_id(self, bundle_id: int) -> IBundle:
        """
        Get bundle by bundle.id
        """

    @abc.abstractmethod
    def get_bundles(self) -> list[IBundle]:
        pass

    @abc.abstractmethod
    def get_property(self, name: str, default: t.Any | None = None) -> t.Any:
        pass

    @abc.abstractmethod
    def get_service(self, reference: IServiceReference) -> t.Any:
        pass

    @abc.abstractmethod
    def unget_service(self, reference: IServiceReference) -> None:
        pass

    @abc.abstractmethod
    def get_service_reference(self, clazz, filter=None):
        pass

    @abc.abstractmethod
    def get_service_references(self, clazz, filter=None):
        pass

    @abc.abstractmethod
    async def install_bundle(self, name, path=None):
        pass

    @abc.abstractmethod
    async def register_service(self, clazz, service, properties=None):
        pass

    @abc.abstractmethod
    def add_framework_listener(self, listener):
        pass

    @abc.abstractmethod
    def add_bundle_listener(self, listener):
        pass

    @abc.abstractmethod
    def add_service_listener(self, listener, interface=None, filter=None):
        pass

    @abc.abstractmethod
    def remove_framework_listener(self, listener):
        pass

    @abc.abstractmethod
    def remove_bundle_listener(self, listener):
        pass

    @abc.abstractmethod
    def remove_service_listener(self, listener):
        pass


class IServiceTrackerListener(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def on_adding_service(self, reference: IServiceReference, service):
        raise NotImplementedError()

    @abc.abstractmethod
    async def on_modified_service(self, reference: IServiceReference, service):
        raise NotImplementedError()

    @abc.abstractmethod
    async def on_removed_service(self, reference: IServiceReference, service):
        raise NotImplementedError()


BUNDLE_EVENTS = {
    1: "INSTALLED",
    2: "STARTED",
    4: "STOPPED",
    8: "UPDATED",
    10: "UNINSTALLED",
    20: "RESOLVED",
    40: "UNRESOLVED",
    80: "STARTING",
    100: "STOPPING",
}


class BundleEvent:
    # Bundle has been installed.
    INSTALLED = 1

    # Bundle has been started.
    STARTED = 2

    # Bundle has been stopped.
    STOPPED = 4

    # Bundle has been updated.
    UPDATED = 8

    # Bundle has been uninstalled.
    UNINSTALLED = 10

    # Bundle has been resolved.
    RESOLVED = 20

    # Bundle has been unresolved.
    UNRESOLVED = 40

    # Bundle is about to be activated.
    STARTING = 80

    # Bundle is about to deactivated.
    STOPPING = 100

    __slots__ = ("__kind", "__bundle", "__origin")

    def __init__(self, kind, bundle, origin=None):
        self.__kind = kind
        self.__bundle = bundle
        self.__origin = origin

    @property
    def kind(self):
        return self.__kind

    @property
    def bundle(self):
        return self.__bundle

    @property
    def origin(self):
        return self.__origin

    def __str__(self):
        return "BundleEvent(kind={}, bundle={})".format(
            BUNDLE_EVENTS[self.__kind], self.__bundle
        )


class FrameworkEvent(BundleEvent):
    pass


SERVICE_EVENTS = {
    1: "REGISTERED",
    2: "MODIFIED",
    4: "UNREGISTERING",
    8: "MODIFIED_ENDMATCH",
}


class ServiceEvent:

    """Service has been registered"""

    REGISTERED = 1

    """ Properties of a registered service have been modified """
    MODIFIED = 2

    """ Service is in the process of being unregistered """
    UNREGISTERING = 4

    """
    Properties of a registered service have been modified and the new
    properties no longer match the listener's filter
    """
    MODIFIED_ENDMATCH = 8

    __slots__ = ("__kind", "__reference", "__properties")

    def __init__(self, kind_, reference, properties=None):
        self.__kind = kind_
        self.__reference = reference
        if properties is None or not isinstance(properties, dict):
            properties = {}
        self.__properties = properties

    @property
    def kind(self):
        return self.__kind

    @property
    def reference(self):
        return self.__reference

    @property
    def previous_properties(self):
        return self.__properties.copy()

    def __str__(self):
        return "ServiceEvent({}, {})".format(
            SERVICE_EVENTS[self.__kind], self.__reference
        )
