import logging

from aiohttp import web

logger = logging.getLogger(__name__)


class Activator:
    def __init__(self):
        self.server_host = "127.0.0.1"
        self.server_port = 8765

    async def start(self, ctx):
        host = ctx.get_property("http.server.host")
        port = ctx.get_property("http.server.port")
        await self.start_server(host, port)

    async def stop(self, ctx):
        logger.info("Stop HTTP")
        await self.site.stop()
        await self.runner.cleanup()

    async def start_server(self, host, port):
        # small hack
        self.app = web.Application(middlewares=[])
        self.app._router.freeze = lambda: None
        context = None
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port, ssl_context=context)

        try:
            logger.info("Start http server http://%s:%d", host, port)
            await self.site.start()
        except OSError as error:
            logger.error("Failed to create HTTP server at port %d: %s", port, error)
