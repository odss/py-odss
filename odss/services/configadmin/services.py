import typing as t
import collections
import uuid

from .interfaces import (
    IConfiguration,
    IConfigurationStorage,
    IConfigurationDirectory,
    IConfigurationAdmin,
    IConfigurationManaged,
    IConfigurationManagedFactory,
    TProperties,
)
from .consts import SERVICE_PID, FACTORY_PID
from .configuration import Configuration, ConfigurationDirectory


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
        self.__managed[pid].add(service)
        await self.__notify_service(pid, service)

    async def remove_managed_service(
        self, pid: str, service: IConfigurationManaged
    ) -> None:
        self.__managed[pid].remove(service)
        if not self.__managed[pid]:
            del self.__managed[pid]

    async def add_managed_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ) -> None:
        self.__managed_factory[factory_pid].add(factory)
        await self.__notify_factory(factory_pid, factory)

    async def remove_managed_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ) -> None:
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

        return await self._directory.add(pid, properties, storage)

    def create_factory_configuration(self, factory_pid: str):
        """
        Create a new factory Configuration object with a new PID.
        """
        pid = f"{factory_pid}-{str(uuid.uuid4())}"
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
                await self.__notify_update_factories(factories, pid, properties)
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

        if factory_pid:
            if factory_pid in self.__managed_factory:
                factories = self.__managed_factory[factory_pid]
                await self.__notify_remove_factories(factories, pid)
        else:
            if pid in self.__managed:
                services = self.__managed[pid]
                await self.__notify_services(services, None)

    async def __notify_service(self, pid: str, service: t.Any):
        if self.has_configuration(pid):
            configuration = await self.get_configuration(pid)
            if configuration.is_valid():
                await service.updated(configuration.get_properties())

    async def __notify_factory(
        self, factory_pid: str, factory: IConfigurationManagedFactory
    ):
        configurations = self._directory.get_factory_configurations(factory_pid)
        for configuration in configurations:
            if configuration.is_valid():
                await factory.updated(
                    configuration.get_pid(), configuration.get_properties()
                )

    async def __notify_pids(self, pids: t.List[str]) -> None:
        for pid in pids:
            configuration = await self.get_configuration(pid)
            if configuration.is_valid():
                await self.__update(configuration)

    async def __notify_update_factories(
        self,
        factories: t.Iterable[IConfigurationManagedFactory],
        pid: str,
        properties: TProperties,
    ):
        for factory in factories:
            await factory.updated(pid, properties)

    async def __notify_remove_factories(
        self, factories: t.Iterable[IConfigurationManagedFactory], pid: str
    ):
        for factory in factories:
            await factory.removed(pid)

    async def __notify_services(
        self, services: IConfigurationManaged, properties: t.Optional[TProperties]
    ):
        for service in services:
            await service.updated(properties)
