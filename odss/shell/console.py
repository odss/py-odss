import asyncio
import logging
import code


from . import SERVICE_SHELL  # , SERVICE_SHELL_COMMAND
from .session import Session

logger = logging.getLogger(__name__)


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        print(f"{__name__} Activator::start()")
        loop = asyncio.get_event_loop()

        self.console = InteractiveConsole(ctx, loop)
        await self.console.start()
        print(f"{__name__} Activator::start() ::post")

    async def stop(self, ctx):
        print(f"{__name__} Activator::stop()")
        await self.console.stop()
        print(f"{__name__} Activator::stop() ::post")


class InteractiveConsole(code.InteractiveConsole):
    def __init__(self, ctx, loop):
        self.ctx = ctx
        self.session = Session()
        self.shell = None
        self.shell_ref = None

    async def start(self):

        self.shell_event = asyncio.Event()
        self.search_shell()
        self.ctx.add_service_listener(self, SERVICE_SHELL)
        self.task = asyncio.create_task(self.run())

    async def stop(self):
        self.ctx.remove_service_listener(self)

        if not self.task.done():
            self.task.cancel()
        if self.shell_ref:
            self.ctx.unget_service(self.shell_ref)

        self.shell = None
        self.shell_ref = None
        self.shell_event = None

    def search_shell(self):
        if self.shell is not None:
            return

        ref = self.ctx.get_service_reference(SERVICE_SHELL)
        if ref is not None:
            self.set_shell(ref)

    def set_shell(self, ref):
        self.shell = self.ctx.get_service(ref)
        self.shell_ref = ref
        self.shell_event.set()

    async def run(self):
        print("InteractiveShell::run()")
        await self.shell_event.wait()

        while True:
            line = await self.session.readline()
            # await self.session.write_line(f"Say: {line}")
            await self.shell.execute(line, self.session)

    async def service_changed(self, event):
        print(f"{__name__}::service_changed({event})")
