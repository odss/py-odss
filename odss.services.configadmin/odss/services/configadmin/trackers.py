from odss.common import (
    SERVICE_PID,
    SERVICE_FACTORY_PID,
    IConfigurationManaged,
    IConfigurationManagedFactory,
    IConfigurationStorage,
    ServiceTracker,
)
from .services import ConfigurationAdmin


class ManagedTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, IConfigurationManaged)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        pid = reference.get_property(SERVICE_PID)
        await self.admin.add_managed_service(pid, service)

    async def on_removed_service(self, reference, service):
        pid = reference.get_property(SERVICE_PID)
        await self.admin.remove_managed_service(pid, service)


class ManagedFactoryTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, IConfigurationManagedFactory)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        # pid = reference.get_property(SERVICE_PID)
        factory_pid = reference.get_property(SERVICE_FACTORY_PID)
        await self.admin.add_managed_factory(factory_pid, service)

    async def on_removed_service(self, reference, service):
        # pid = reference.get_property(SERVICE_PID)
        factory_pid = reference.get_property(SERVICE_FACTORY_PID)
        await self.admin.remove_managed_factory(factory_pid, service)


class StorageTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, IConfigurationStorage)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        await self.admin.add_storage(service)

    async def on_removed_service(self, reference, service):
        await self.admin.remove_storage(service)
