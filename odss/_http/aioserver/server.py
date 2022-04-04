import asyncio
import functools
import logging
import typing as t

from aiohttp import web

from odss.http import IHttpServer, IHttpContext
from odss.http.base import Middlewares, MiddlewareTracker, RouteTracker

from .context import HttpContext


__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)


logger = logging.getLogger(__name__)


class Activator:
    async def start(self, ctx):
        host = ctx.get_property("http.server.host")
        port = ctx.get_property("http.server.port")
        self.server = HttpServer(host, port)
        self.rtracker = RouteTracker(ctx, self.server)
        self.mtracker = MiddlewareTracker(ctx, self.server)
        await self.server.open()
        await self.rtracker.open()
        await self.mtracker.open()
        self.reg = ctx.register_service(IHttpServer, self.server, {"type": "http"})

    async def stop(self, ctx):
        logger.info("Stop http server")
        self.reg.unregister()
        await self.mtracker.close()
        await self.rtracker.close()
        await self.server.close()


class ServerMiddlewares(Middlewares):
    def freeze(self):
        pass

    def __reversed__(self):
        return [self.handle_middleware]

    @web.middleware
    async def handle_middleware(self, request, handler):
        ctx = HttpContext(request)
        for mid, p in self.middlewares[::-1]:
            handler = functools.partial(mid, handler=handler)
        return await handler(ctx)


class HttpServer(IHttpServer):
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port

        self._handlers = {}
        self._middlewares = ServerMiddlewares()

    async def open(self):
        self.app = web.Application(middlewares=[])
        self.app._router.freeze = lambda: None  # remove freeze
        self.app._middlewares = self._middlewares

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=None)

        try:
            logger.info("Start http server http://%s:%d", self.host, self.port)
            await self.site.start()
        except OSError as error:
            logger.error(
                "Failed to create HTTP server at port %d: %s", self.port, error
            )

    async def close(self):
        await self.site.stop()
        await self.runner.shutdown()
        self.site = None
        self.runner = None
        self.app = None

    def register_route(
        self, methods: t.List[str], path: str, name: str, handler: t.Callable
    ) -> t.Callable[[], None]:
        handler = request_handler_factory(handler)
        logger.info("Add route: %s %s (name=%s)", methods, path, name)
        route = self.app.router.add_route(methods, path, handler, name=name)

        def unregister_route():
            logger.info("Remove route: %s %s (name=%s)", methods, path, name)
            resource = route.resource
            resource._routes.remove(route)
            if not resource._routes and self.app:
                router = self.app.router
                router._resources.remove(resource)
                if resource.name:
                    del router._named_resources[resource.name]

        return unregister_route

    def add_middleware(self, middleware: t.Callable, priority: int = 0):
        return self._middlewares.add(middleware, priority)


def request_handler_factory(handler: t.Callable) -> t.Callable:
    """Wrap handler."""

    async def handle(ctx: IHttpContext) -> web.StreamResponse:
        """Handle incoming request."""
        result = handler(ctx, **ctx.request.match_info)
        if asyncio.iscoroutine(result):
            result = await result

        if isinstance(result, web.StreamResponse):
            return result

        status_code = 200

        if isinstance(result, tuple):
            result, status_code = result

        if isinstance(result, bytes):
            body = result
        elif isinstance(result, str):
            body = result.encode("utf-8")
        elif result is None:
            body = b""
        else:
            assert (
                False
            ), f"Result should be None, string, bytes or Response. Got: {result}"

        return web.Response(body=body, status=status_code)

    return handle
