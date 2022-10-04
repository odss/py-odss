from odss.shell.decorators import command
from odss.shell.consts import SERVICE_SHELL_COMMANDS
from odss.shell.utils import make_ascii_table

from .abc import IConfigurationAdmin, IConfigurationStorage
from .services import ConfigurationAdmin
from .storages import MemoryStorage, JsonFileStorage
from .trackers import StorageTracker, ManagedTracker, ManagedFactoryTracker


class Activator:
    async def start(self, ctx):
        self.admin = ConfigurationAdmin()
        storage = JsonFileStorage()
        await storage.open()

        await ctx.register_service(IConfigurationAdmin, self.admin)
        # ctx.register_service(IConfigurationStorage, MemoryStorage())

        await ctx.register_service(IConfigurationStorage, storage)
        await ctx.register_service(SERVICE_SHELL_COMMANDS, Commands(self.admin))
        self.trackers = [
            StorageTracker(ctx, self.admin),
            ManagedTracker(ctx, self.admin),
            ManagedFactoryTracker(ctx, self.admin),
        ]
        for tracker in self.trackers:
            await tracker.open()

    async def stop(self, ctx):
        for tracker in self.trackers:
            await tracker.close()
        self.admin = None


class Commands:
    def __init__(self, admin: ConfigurationAdmin):
        self.admin = admin

    @command("list", "cm")
    async def cm_list(self, session):
        """
        List of pids
        """
        items = self.admin.list_configurations()
        return make_ascii_table(
            "List", ["PID"], [[config.get_pid()] for config in items]
        )

    @command("create", "cm")
    async def cm_create(self, session, pid, sufix=None):
        """
        Remove of selected configuraton pid
        """
        config = await self.admin.create_factory_configuration(pid, sufix)
        return config.get_pid()

    @command("del", "cm")
    async def cm_del(self, session, pid):
        """
        Remove of selected configuraton pid
        """
        config = await self.admin.get_configuration(pid)
        await config.remove()

    @command("get", "cm")
    async def cm_get(self, session, pid):
        """
        Properties of selected configuration
        """
        config = await self.admin.get_configuration(pid)
        lines = [(name, str(value)) for name, value in config.get_properties().items()]
        return make_ascii_table(f"Properties: {pid}", ["Property name", "Value"], lines)

    @command("set", "cm")
    async def cm_set(self, session, pid, name, value):
        """
        Set value to selected pid
        """
        config = await self.admin.get_configuration(pid)
        await config.update({name: value})

    @command("reload", "cm")
    async def cm_reload(self, session, pid):
        """
        Reload selected pid
        """
        config = await self.admin.get_configuration(pid)
        await config.reload()
