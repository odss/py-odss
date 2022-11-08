import abc
import typing as t

from .base import TProperties


class IConfigurationManaged(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def updated(self, properties: t.Optional[TProperties]):
        """
        Called when instance is reconfigured.
        """


class IConfigurationManagedFactory(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def updated(self, pid: str, properties: TProperties):
        """
        Called when instance is reconfigured.
        """

    @abc.abstractmethod
    async def deleted(self, pid: str):
        """
        Called when instance is removed.
        """


class IConfiguration(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_bundle_location(self) -> str:
        """
        Get the bundle location.
        """

    @abc.abstractmethod
    def get_factory_pid(self) -> str:
        """
        For a factory configuration return the PID of the corresponding Managed Service Factory, else return null.
        """

    @abc.abstractmethod
    def get_pid(self) -> str:
        """
        Get the PID for this Configuration object.
        """

    @abc.abstractmethod
    def get_properties(self) -> t.Dict:
        """
        Return the properties of this Configuration object.
        """

    @abc.abstractmethod
    def set_bundle_location(self, bundle_location: str) -> None:
        """
        Bind this Configuration object to the specified bundle location.
        """

    @abc.abstractmethod
    async def update(self, properties: TProperties = None) -> None:
        """
        Update the Configuration object with the current properties.
        """

    @abc.abstractmethod
    async def remove(self) -> None:
        """
        Remove the Configuration object.
        """

    @abc.abstractmethod
    async def reload(self):
        """
        Reload the Configuration object.
        """


class IConfigurationStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def store(self, pid: str, properties: TProperties):
        """
        Save properties from store
        """

    @abc.abstractmethod
    async def load(self, pid: str) -> t.Optional[TProperties]:
        """
        Load properties from store
        """

    @abc.abstractmethod
    async def remove(self, pid: str) -> None:
        """
        Remove properties from store
        """

    @abc.abstractmethod
    async def exists(self, pid: str) -> bool:
        """
        Check exists properties in store
        """

    @abc.abstractmethod
    async def get_pids(self) -> t.Iterable[str]:
        """
        Return all pids in store
        """


class IConfigurationDirectory(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get(self, pid: str) -> IConfiguration:
        """
        Return configuraton
        """

    @abc.abstractmethod
    async def add(
        self,
        pid: str,
        properties: TProperties,
        storage: IConfigurationStorage,
        factory_pid: str = None,
    ) -> IConfiguration:
        """
        Add new configuration
        """

    @abc.abstractmethod
    def exists(self, pid: str) -> bool:
        """
        Check exists configuration in directory
        """

    @abc.abstractmethod
    async def remove(self, pid: str) -> None:
        """
        Remove configuration fom directory
        """


class IConfigurationAdmin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_configuration(self, pid: str) -> IConfiguration:
        """
        Get an existing Configuration object from the persistent store, or create a new Configuration object.
        """

    @abc.abstractmethod
    def create_factory_configuration(self, factory_pid: str):
        """
        Create a new factory Configuration object with a new PID.
        """

    @abc.abstractmethod
    def list_configurations(self, ldap_filter=None) -> t.Iterable[IConfiguration]:
        """
        List the current Configuration objects which match the filter."
        """
