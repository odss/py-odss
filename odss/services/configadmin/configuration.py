import typing as t
import collections

from odss.core.query import create_query
from .interfaces import (
    IConfiguration,
    IConfigurationStorage,
    TProperties,
)
from .consts import SERVICE_PID, FACTORY_PID


class Configuration(IConfiguration):
    def __init__(
        self,
        pid: str,
        admin: "ConfigurationAdmin",
        storage: IConfigurationStorage,
        factory_pid: str = None,
    ):
        self.__pid = pid
        self.__factory_pid = factory_pid

        self.__revision = 1
        self.__properties = {}
        self.__location = None

        self.__updated = False
        self.__removed = False

        # Associated services
        self.__admin = admin
        self.__storage = storage

    def set_bundle_location(self, bundle_location: str) -> None:
        self.__location = bundle_location

    def get_bundle_location(self) -> str:
        return self.__location

    def get_factory_pid(self) -> str:
        return self.__factory_pid

    def get_pid(self) -> str:
        return self.__pid

    def get_properties(self) -> t.Dict:
        if self.__removed:
            raise ValueError(f"Configuration: {self.__pid} was removed")
        return self.__properties.copy()

    def is_valid(self) -> bool:
        return self.__updated and not self.__removed

    async def update(self, properties: TProperties, replace: bool = False) -> None:
        if await self._update_properties(properties, replace):
            await self.__admin.on_update(self)

    async def _update_properties(
        self, properties: TProperties, replace: bool = False
    ) -> bool:
        if not properties:
            return False

        properties = properties.copy()

        properties[SERVICE_PID] = self.__pid
        if self.__factory_pid:
            properties[FACTORY_PID] = self.__factory_pid

        if properties == self.__properties:
            return False

        if replace:
            self.__properties = properties.copy()
        else:
            self.__properties.update(properties)

        self.__updated = True
        await self.__storage.save(self.__pid, self.__properties)
        return True

    async def remove(self) -> None:
        if self.__removed:
            return

        self.__removed = True

        await self.__storage.remove(self.__pid)
        await self.__admin.on_remove(self)

        if self.__properties:
            self.__properties.clear()

        self.__properties = None
        self.__pid = None

    async def reload(self):
        properties = await self.__storage.load(self.__pid)
        await self.update(properties)

    def __str__(self):
        return f"Configuration(pid={self.__pid}, updated={self.__updated}, deleted={self.__removed})"


class ConfigurationDirectory:
    def __init__(self, admin: "ConfigurationAdmin"):
        self.__admin = admin
        self.__configurations = {}
        self.__factories = collections.defaultdict(set)

    def get(self, pid: str) -> IConfiguration:
        configs = self.__configurations
        return self.__configurations[pid]

    async def add(
        self,
        pid: str,
        properties: TProperties,
        storage: IConfigurationStorage,
        factory_pid: str = None,
    ) -> IConfiguration:
        configuration = Configuration(pid, self.__admin, storage, factory_pid)
        await configuration._update_properties(properties)
        self.__configurations[pid] = configuration

        if factory_pid is not None:
            self.__factories[factory_pid].add(configuration)
        return configuration

    def exists(self, pid: str) -> bool:
        return pid in self.__configurations

    async def remove(self, pid: str) -> None:
        configuration = self.__configurations.pop(pid)
        factory_pid = configuration.get_factory_pid()
        try:
            factory_confs = self.__factories[factory_pid]
            factory_confs.remove(configuration)
            if not factory_confs:
                del self.__factories[factory_pid]
        except KeyError:
            pass

        await configuration.remove()

    async def update(self, pid: str, properties: TProperties, replace: bool = False):
        await self.__configurations[pid].update(properties, replace)

    def get_factory_configurations(self, factory_pid):
        return set(self.__factories.get(factory_pid, tuple()))

    def list_configurations(
        self, ldap_filter: t.Any = None
    ) -> t.Iterable[IConfiguration]:
        if ldap_filter is None:
            return list(self.__configurations.values())

        matcher = create_query(ldap_filter)
        return [
            configuration
            for configuration in self.__configurations.values()
            if matcher.match(configuration.get_properties())
        ]
