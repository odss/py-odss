import logging
import threading
from aiohttp import web

logger = logging.getLogger(__name__)


class Activator:
    def __init__(self):
        self.server_host = "127.0.0.1"
        self.server_port = 8765

    async def start(self, context):
        print("Start HTTP")
        print(threading.current_thread().name)
        await self.start_server()

    async def stop(self, context):
        print("Stop HTTP")
        await self.site.stop()
        await self.runner.cleanup()

    async def start_server(self):
        # small hack
        self.app = web.Application(middlewares=[])
        self.app._router.freeze = lambda: None
        context = None
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(
            self.runner, self.server_host, self.server_port, ssl_context=context
        )

        try:
            print(f'Start http server http://{self.server_host}:{self.server_port}')
            await self.site.start()
        except OSError as error:
            logger.error(
                "Failed to create HTTP server at port %d: %s", self.server_port, error
            )
