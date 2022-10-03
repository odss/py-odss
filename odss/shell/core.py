from ..core.trackers import ServiceTracker
from .consts import SERVICE_SHELL, SERVICE_SHELL_COMMANDS
from .shell import Shell


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        self.shell = Shell(ctx, bind_basic=True)
        self.tracker = CommandTracker(ctx, self.shell)

        await ctx.register_service(SERVICE_SHELL, self.shell)
        await self.tracker.open()

    async def stop(self, ctx):
        await self.tracker.close()


class CommandTracker(ServiceTracker):
    def __init__(self, ctx, shell):
        super().__init__(self, ctx, SERVICE_SHELL_COMMANDS)
        self.shell = shell

    def on_adding_service(self, reference, service):
        self.shell.bind_handler(service)

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        self.shell.unbind_handler(service)
