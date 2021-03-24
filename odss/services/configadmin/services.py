import typing as t
import collections
import uuid

from odss.core.query import create_query
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


class ConfigurationAdminListener:
    def __init__(self, admin: "ConfigurationAdmin"):
        self.admin = admin

    async def on_update(self, configuration: IConfiguration):
        await self.admin.on_update(configuration)

    async def on_remove(self, configuration: IConfiguration):
        await self.admin.on_remove(configuration)


class Configuration(IConfiguration):
    def __init__(
        self,
        pid: str,
        admin_listener: ConfigurationAdminListener,
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
        self.__admin_listener = admin_listener
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

    async def update(self, properties: TProperties, replace: bool = False) -> bool:
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
        await self.__admin_listener.on_update(self)
        return True

    async def remove(self) -> None:
        if self.__removed:
            return

        self.__removed = True

        await self.__storage.remove(self.__pid)
        await self.__admin_listener.on_remove(self)

        if self.__properties:
            self.__properties.clear()

        self.__properties = None
        self.__pid = None

    async def reload(self):
        properties = await self.__storage.load(self.__pid)
        await self.update(properties)

    def __str__(self):
        """
        String representation
        """
        return f"Configuration(pid={self.__pid}, updated={self.__updated}, deleted={self.__removed})"


class ConfigurationDirectory:
    def __init__(self, admin_listener: ConfigurationAdminListener):
        self.__admin_listener = admin_listener
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
        configuration = Configuration(pid, self.__admin_listener, storage, factory_pid)
        await configuration.update(properties)
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


class ConfigurationAdmin(IConfigurationAdmin):
    def __init__(self):
        self._directory = ConfigurationDirectory(ConfigurationAdminListener(self))
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
            await self.get_configuration(pid)
            # if configuration.is_valid():
            #     await self.__update(configuration)

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
