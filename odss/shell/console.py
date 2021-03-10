import asyncio

from .consts import SERVICE_SHELL  # , SERVICE_SHELL_COMMAND
from .session import Session
from ..core.trackers import ServiceTracker


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        self.console = InteractiveConsole(ctx)
        await self.console.start()

    async def stop(self, ctx):
        await self.console.stop()


class InteractiveConsole(ServiceTracker):
    def __init__(self, ctx):
        super().__init__(self, ctx, SERVICE_SHELL)
        self.session = Session(self)
        self.shell = None

    async def start(self):
        await self.open()

    async def stop(self):
        await self.close()

    def get_completions(self, line):
        if self.shell:
            return self.shell.get_all_commands()
        return []

    def on_adding_service(self, reference, service):
        if not self.shell:
            self.shell = service
            self.task = asyncio.create_task(self.run())

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        self.shell = None
        if not self.task.done():
            self.task.cancel()

    async def run(self):
        while self.shell:
            line = await self.session.readline()
            if self.shell:
                await self.shell.execute(self.session, line)
