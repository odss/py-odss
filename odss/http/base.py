import inspect
import bisect
import logging
import typing as t

from odss.core.trackers import ServiceTracker
from odss.core.bundle import IBundleContext
from odss.http.abc import IHttpServer
from odss.http.consts import (
    ODSS_HTTP_ROUTE_HANDLER,
    SERVICE_HTTP_ROUTE,
    SERVICE_HTTP_MIDDLEWARE,
)

logger = logging.getLogger(__name__)


HandlerInfo = t.Tuple[t.Callable, t.Dict[str, t.Any]]


class RouteTracker(ServiceTracker):
    def __init__(self, ctx: IBundleContext, server: IHttpServer):
        super().__init__(self, ctx, SERVICE_HTTP_ROUTE)
        self.server = server
        self.handlers = {}

    def on_adding_service(self, reference, service):
        self.bind_handler(service)

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        self.unbind_handler(service)

    def bind_handler(self, handler: t.Any):
        """
        Bind handler
        """
        if handler in self.handlers:
            logger.warning("Handler already register: %s", handler)
            return False

        routes = []
        for handler, attrs in self._extract_handlers(handler):
            name = attrs.pop("name")
            path = attrs.pop("path")
            methods = attrs.pop("methods")
            unregister = self.server.register_route(methods, path, name, handler)
            routes.append(unregister)

        self.handlers[handler] = routes
        return True

    def unbind_handler(self, handler: t.Any):
        """
        Unbind handler
        """
        if handler not in self.handlers:
            logger.warning("Handler not found: %s", handler)
            return False

        unregisters = self.handlers[handler]
        for unregister in unregisters:
            unregister()

        del self.handlers[handler]

        return True

    @staticmethod
    def _extract_handlers(obj: t.Any) -> HandlerInfo:
        handlers = [
            fn
            for name, fn in inspect.getmembers(obj, inspect.isroutine)
            if not name.startswith("_")
        ]
        for handler in handlers:
            options = getattr(handler, ODSS_HTTP_ROUTE_HANDLER, None)
            if options:
                yield handler, options.copy()


class MiddlewareTracker(ServiceTracker):
    def __init__(self, ctx: IBundleContext, server: IHttpServer):
        super().__init__(self, ctx, SERVICE_HTTP_MIDDLEWARE)
        self.server = server
        self.subs = {}

    def on_adding_service(self, reference, service):
        self.subs[service] = self.server.add_middleware(
            service, reference.get_sort_value()
        )

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        if self.subs[service]:
            self.subs[service]()
            del self.subs[service]


class Middlewares:
    def __init__(self):
        self.middlewares = []

    def add(self, middleware: t.Callable, priority: t.Tuple[int] = None):
        priority = priority if priority is not None else (0, 0)
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.insert(idx, (middleware, priority))

        def remove_middleware():
            self.remove(middleware, priority)

        return remove_middleware

    def remove(self, middleware: t.Callable, priority: t.Tuple[int] = None):
        priority = priority if priority is not None else (0, 0)
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.pop(idx)
