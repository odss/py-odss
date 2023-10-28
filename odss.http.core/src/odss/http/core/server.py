import functools
import inspect
import logging
import typing as t

from odss.http.common import (
    ODSS_HTTP_HANDLER,
    ODSS_HTTP_VIEW,
    IHttpServer,
    IHttpServerEngineFactory,
    RouteInfo,
)

from .handlers import create_request_handler
from .middewares import Middlewares

logger = logging.getLogger(__name__)

HandlerInfo = tuple[t.Callable, dict[str, t.Any]]


def extract_handlers(obj: t.Any) -> t.Iterator[HandlerInfo]:
    if hasattr(obj, ODSS_HTTP_HANDLER):
        yield obj, getattr(obj, ODSS_HTTP_HANDLER)
    else:
        handlers = [
            fn
            for name, fn in inspect.getmembers(obj, inspect.isroutine)
            if not name.startswith("_")
        ]
        for handler in handlers:
            props = getattr(handler, ODSS_HTTP_HANDLER, None)
            if props:
                yield handler, props


def extract_view_prefix(view: t.Any) -> str:
    try:
        prefix = getattr(view, ODSS_HTTP_VIEW)["prefix"]
        if prefix:
            assert prefix.startswith("/")
            assert not prefix.endswith("/")
            assert len(prefix) > 1
        return prefix
    except (KeyError, AttributeError):
        pass
    return ""


class HttpServer(IHttpServer):
    def __init__(
        self, engine_factory: IHttpServerEngineFactory, host: str, port: int
    ) -> None:
        self.middlewares = Middlewares()
        self.engine_factory = engine_factory
        self.engine = None
        self.handlers: dict[t.Any, list[t.Callable]] = {}
        self.host = host
        self.port = port

    async def open(self):
        self.engine = self.engine_factory.create(
            self.request_handler, self.host, self.port
        )
        await self.engine.open()

    async def close(self):
        await self.engine.close()
        self.middlewares.reset()
        self.engine_factory = None
        self.engine = None

    def add_route(self, route):
        return self.engine.add_route(route)

    def add_middleware(
        self, middleware: t.Callable, priority: tuple[int, int]
    ):
        return self.middlewares.add(middleware, priority)

    def request_handler(self, handler, request):
        request.is_secure = request.secure
        settings = getattr(handler, ODSS_HTTP_HANDLER, {})
        setattr(request, "settings", settings)

        for middleware, _ in self.middlewares.all():
            handler = functools.partial(middleware, handler=handler)
        return handler(request)

    def bind_handler(self, view: t.Any):
        if view in self.handlers:
            logger.warning("Handler is already register: %s", view)
            return False

        prefix = extract_view_prefix(view)
        routes = []
        for handler, props in extract_handlers(view):
            path = prefix + props["path"]
            handler = create_request_handler(path, props, handler)
            route = RouteInfo(props["name"], props["method"], path, handler, props)
            unregister = self.add_route(route)
            routes.append(unregister)

        self.handlers[view] = routes
        return True

    def unbind_handler(self, view: t.Any):
        if view not in self.handlers:
            logger.warning("Handler not found: %s", view)
            return False

        unregisters = self.handlers[view]
        for unregister in unregisters:
            unregister()

        del self.handlers[view]

        return True

