from odss.core.trackers import ServiceTracker

from .consts import (
    SERVICE_PID,
    FACTORY_PID,
    SERVICE_CONFIGURATION_ADMIN,
    SERVICE_CONFIGADMIN_MANAGED,
    SERVICE_CONFIGADMIN_MANAGED_FACTORY,
    SERVICE_CONFIGADMIN_STORAGE,
)
from .services import ConfigurationAdmin


class Activator:
    async def start(self, ctx):
        admin = ConfigurationAdmin()
        self.trackers = [
            StorageTracker(ctx, admin),
            ManagedTracker(ctx, admin),
            ManagedFactoryTracker(ctx, admin),
        ]
        for tracker in self.trackers:
            await tracker.open()

        await ctx.register_service(SERVICE_CONFIGURATION_ADMIN, self.admin)

    async def stop(self, ctx):
        for tracker in self.trackers:
            await tracker.close()


class ManagedTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, SERVICE_CONFIGADMIN_MANAGED)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        pid = reference.get_property(SERVICE_PID)
        await self.admin.add_managed_service(pid, service)

    async def on_removed_service(self, reference, service):
        pid = reference.get_property(SERVICE_PID)
        await self.admin.remove_managed_service(pid, service)


class ManagedFactoryTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, SERVICE_CONFIGADMIN_MANAGED_FACTORY)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        # pid = reference.get_property(SERVICE_PID)
        factory_pid = reference.get_property(FACTORY_PID)
        await self.admin.add_managed_factory(factory_pid, service)

    async def on_removed_service(self, reference, service):
        # pid = reference.get_property(SERVICE_PID)
        factory_pid = reference.get_property(FACTORY_PID)
        await self.admin.remove_managed_factory(factory_pid, service)


class StorageTracker(ServiceTracker):
    def __init__(self, ctx, admin: ConfigurationAdmin):
        super().__init__(self, ctx, SERVICE_CONFIGADMIN_STORAGE)
        self.admin = admin

    async def on_adding_service(self, reference, service):
        await self.admin.add_storage(service)

    async def on_removed_service(self, reference, service):
        await self.admin.remove_storage(service)
