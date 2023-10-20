import asyncio
import functools
import logging
import typing as t

from aiohttp import web
from odss.http.common import Request, Response, RouteInfo, HttpError

logger = logging.getLogger(__name__)


Handler = t.Callable[[Request], t.Awaitable[Response]]

RequestHandler = t.Callable[[Handler, Request], t.Awaitable[Response]]


async def route_handler(handler: Handler, request: Request) -> web.Response:
    response = handler(request)
    if asyncio.iscoroutine(response):
        response = await response
    return response


class ServerEngineFactory:
    def create(self, request_handler: RequestHandler, host: str, port: int):
        return ServerEngine(request_handler, host, port)


class Application(web.Application):
    def __init__(self, request_handler: RequestHandler) -> None:
        super().__init__(middlewares=[])
        self.request_handler = request_handler

    async def _handle(self, request: Request) -> web.StreamResponse:
        match_info = await self._router.resolve(request)
        request._match_info = match_info
        try:
            response = await self.request_handler(match_info.handler, request)
            response.finish()
            return web.Response(
                body=response.body,
                status=response.code,
                content_type=response.content_type,
                charset=response.charset,
                headers=response.headers,
            )
        except HttpError as ex:
            return web.json_response(
                ex.to_json(),
                status=ex.code,
                reason=ex.status,
                content_type=ex.content_type,
                # charset=ex.charset,
                headers=ex.headers,
            )


class ServerEngine:
    def __init__(
        self, request_handler: RequestHandler, host: str = "0.0.0.0", port: int = 8765
    ):
        self.request_handler = request_handler
        self.host = host
        self.port = port

    async def open(self):
        self.app = Application(self.request_handler)
        self.app._router.freeze = lambda: None  # remove freeze
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=None)
        await self.site.start()

    async def close(self):
        logger.info("Stop http server http://%s:%d", self.host, self.port)
        await self.site.stop()
        await self.runner.shutdown()
        self.site = None
        self.runner = None
        self.app = None

    def add_route(
        self,
        route_info: RouteInfo,
    ) -> t.Callable[[], None]:
        logger.info(
            "Add route: %s %s (name=%s)",
            route_info.method,
            route_info.path,
            route_info.name,
        )
        handler = functools.partial(route_handler, route_info.handler)
        app_route = self.app.router.add_route(
            route_info.method, route_info.path, handler, name=route_info.name
        )

        def unregister_route(app_route):
            logger.info(
                "Remove route: %s %s (name=%s)",
                route_info.method,
                route_info.path,
                route_info.name,
            )
            resource = app_route.resource
            resource._routes.remove(app_route)
            if not resource._routes and self.app:
                router = self.app.router
                router._resources.remove(resource)
                if resource.name:
                    del router._named_resources[resource.name]

        return functools.partial(unregister_route, app_route)
