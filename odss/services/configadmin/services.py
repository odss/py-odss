import asyncio
from multiprocessing.sharedctypes import Value
from re import I
import uuid
import typing as t
import collections

from odss.core.query import create_query
from .consts import SERVICE_PID, SERVICE_FACTORY_PID

from .abc import (
    IConfiguration,
    IConfigurationStorage,
    IConfigurationDirectory,
    IConfigurationAdmin,
    IConfigurationManaged,
    IConfigurationManagedFactory,
    TProperties,
)


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

        self.__properties = {}
        self.__location = None

        self.__updated = False
        self.__removed = False

        # Associated services
        self.__admin = admin
        self.__storage = storage

    def set_bundle_location(self, location: str) -> None:
        self.__location = location

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
        if properties is None:
            return False

        properties = properties.copy()

        properties[SERVICE_PID] = self.__pid
        if self.__factory_pid:
            properties[SERVICE_FACTORY_PID] = self.__factory_pid

        if properties == self.__properties:
            return False

        if replace:
            self.__properties = properties.copy()
        else:
            self.__properties.update(properties)

        self.__updated = True
        await self.__storage.store(self.__pid, self.__properties)

        return True

    async def remove(self) -> None:
        if self.__removed:
            return
        self.__removed = True

        await self.__storage.remove(self.__pid)
        await self.__admin.on_remove(self)

        if self.__properties:
            self.__properties.clear()

        self.__storage = None
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
        """
        Get exists configuration
        """
        return self.__configurations[pid]

    async def add(
        self,
        pid: str,
        properties: TProperties,
        storage: IConfigurationStorage,
        factory_pid: str = None,
        store: bool = False
    ) -> IConfiguration:
        if not pid:
            raise ValueError("Configuration with an empty PID")

        if pid in self.__configurations:
            raise ValueError("Already known configuration: {0}".format(pid))

        if pid in self.__factories:
            raise ValueError("PID already used as a factory PID: {0}".format(pid))

        if storage is None:
            raise ValueError("No storage service associated to {0}".format(pid))

        configuration = Configuration(pid, self.__admin, storage, factory_pid)
        await configuration._update_properties(properties)
        self.__configurations[pid] = configuration

        if factory_pid is not None:
            self.__factories[factory_pid].add(configuration)
        return configuration

    def exists(self, pid: str) -> bool:
        return pid in self.__configurations

    async def remove(self, pid: str) -> None:
        if pid in self.__configurations:
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


class ConfigurationAdmin(IConfigurationAdmin):
    def __init__(self):
        self._directory = ConfigurationDirectory(self)
        self._storages: t.List[IConfigurationStorage] = []
        self.__managed = collections.defaultdict(set)
        self.__managed_factory = collections.defaultdict(set)

    def get_directory(self) -> IConfigurationDirectory:
        return self._directory

    async def add_storage(self, storage: IConfigurationStorage) -> None:
        if storage in self._storages:
            raise ValueError(f"Storage: {storage} already exists")
        self._storages.append(storage)
        pids = await storage.get_pids()
        await self.__notify_pids(pids)

    async def remove_storage(self, storage: IConfigurationStorage) -> None:
        self._storages.remove(storage)

    async def add_managed_service(
        self, pid: str, service: IConfigurationManaged
    ) -> None:
        if not pid:
            raise ValueError("Managed without PID")

        self.__managed[pid].add(service)
        if self._storages:
            await self.__notify_service(pid, service)

    async def remove_managed_service(
        self, pid: str, service: IConfigurationManaged
    ) -> None:
        if not pid:
            raise ValueError("Managed without PID")

        self.__managed[pid].remove(service)
        if not self.__managed[pid]:
            del self.__managed[pid]

    async def add_managed_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ) -> None:
        if not factory_pid:
            raise ValueError("Managed Factory without Factory PID")

        self.__managed_factory[factory_pid].add(factory)
        if self._storages:
            await self.__notify_factory(factory_pid, factory)

    async def remove_managed_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ) -> None:
        if not factory_pid:
            raise ValueError("Managed Factory without Factory PID")

        self.__managed_factory[factory_pid].remove(factory)
        if not self.__managed_factory[factory_pid]:
            del self.__managed_factory[factory_pid]

    def has_configuration(self, pid: str) -> bool:
        return self._directory.exists(pid)

    async def get_configuration(self, pid: str) -> IConfiguration:
        """
        Get an existing Configuration object from the persistent store, or create a new Configuration object.
        """
        try:
            return self._directory.get(pid)
        except KeyError:
            pass

        for storage in self._storages[:]:
            if await storage.exists(pid):
                properties = await storage.load(pid)
                break
        else:
            storage = self._storages[0]
            properties = {}

        # lets check factory pid
        factory_pid = properties.get(SERVICE_FACTORY_PID)

        return await self._directory.add(pid, properties, storage, factory_pid)

    def create_factory_configuration(self, factory_pid: str, sufix: str = None):
        """
        Create a new factory Configuration object with a new PID.
        """
        if factory_pid is None:
            raise ValueError("No found factory PID")
        try:
            factory_pid = factory_pid.strip()
            if not factory_pid:
                raise ValueError("Empty factory PID")
        except AttributeError:
            raise ValueError("Incorrect type of factory PID")

        sufix = sufix if sufix else str(uuid.uuid4())
        pid = f"{factory_pid}-{sufix}"
        return self._directory.add(pid, {}, self._storages[0], factory_pid)

    def list_configurations(self, ldap_filter=None) -> t.Iterable[IConfiguration]:
        """
        List the current Configuration objects which match the filter."
        """
        return self._directory.list_configurations(ldap_filter)

    async def on_update(self, configuration: IConfiguration):
        await self.__update(configuration)

    async def on_remove(self, configuration: IConfiguration):
        await self.__remove(configuration)

    async def __update(self, configuration: IConfiguration):
        """
        Notify to update all related managed services
        """
        pid = configuration.get_pid()
        factory_pid = configuration.get_factory_pid()
        properties = configuration.get_properties()
        if factory_pid:
            if factory_pid in self.__managed_factory:
                factories = self.__managed_factory[factory_pid]
                await self.__notify_factories_update(factories, pid, properties)
        else:
            if pid in self.__managed:
                services = self.__managed[pid]
                await self.__notify_services(services, properties)

    async def __remove(self, configuration: IConfiguration):
        """
        Notify to remove all related managed services
        """
        pid = configuration.get_pid()
        factory_pid = configuration.get_factory_pid()

        await self._directory.remove(pid)

        if factory_pid:
            if factory_pid in self.__managed_factory:
                factories = self.__managed_factory[factory_pid]
                await self.__notify_factories_remove(factories, pid)
        else:
            if pid in self.__managed:
                services = self.__managed[pid]
                await self.__notify_services(services, None)

    async def __notify_service(self, pid: str, service: t.Any):
        configuration = await self.get_configuration(pid)
        if configuration.is_valid():
            result = service.updated(configuration.get_properties())
            if asyncio.iscoroutine(result):
                await result

    async def __notify_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ):
        configurations = self._directory.get_factory_configurations(factory_pid)
        for configuration in configurations:
            if configuration.is_valid():
                result = factory.updated(
                    configuration.get_pid(), configuration.get_properties()
                )
                if asyncio.iscoroutine(result):
                    await result

    async def __notify_pids(self, pids: t.List[str]) -> None:
        for pid in pids:
            configuration = await self.get_configuration(pid)
            if configuration.is_valid():
                await self.__update(configuration)

    async def __notify_factories_update(
        self,
        factories: t.Iterable[IConfigurationManagedFactory],
        pid: str,
        properties: TProperties,
    ):
        for factory in factories:
            await factory.updated(pid, properties)

    async def __notify_factories_remove(
        self, factories: t.Iterable[IConfigurationManagedFactory], pid: str
    ):
        for factory in factories:
            await factory.removed(pid)

    async def __notify_services(
        self, services: IConfigurationManaged, properties: t.Optional[TProperties]
    ):
        for service in services:

            result = service.updated(properties)
            if asyncio.iscoroutine(result):
                await result
