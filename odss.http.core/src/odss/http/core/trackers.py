import logging
import typing as t

from odss.common import (
    SERVICE_FACTORY_PID,
    IBundleContext,
    IConfigurationManagedFactory,
    IServiceReference,
    IServiceTrackerListener,
    ServiceTracker,
)
from odss.http.common import IHttpMiddlewareService, IHttpRouteService, IHttpServer, IHttpSecurity

from .engine import ServerEngineFactory
from .server import HttpServer

logger = logging.getLogger(__name__)


class ViewSettings(t.TypedDict):
    prefix: str


class RouteTracker(ServiceTracker, IServiceTrackerListener):
    def __init__(
        self,
        ctx: IBundleContext,
        server: IHttpServer,
        scope: str,
    ):
        query = (
            "|(!(scope=*)(scope=default))" if scope == "default" else {"scope": scope}
        )
        super().__init__(self, ctx, IHttpRouteService, query)
        self.server = server

    def on_adding_service(self, reference, service):
        self.server.bind_handler(service)

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        self.server.unbind_handler(service)


class MiddlewareTracker(ServiceTracker, IServiceTrackerListener):
    def __init__(self, ctx: IBundleContext, server: HttpServer, scope: str):
        query = (
            "|(!(scope=*)(scope=default))" if scope == "default" else {"scope": scope}
        )
        super().__init__(self, ctx, IHttpMiddlewareService, query)
        self.server = server
        self.subs: dict[IServiceReference, t.Any] = {}

    def on_adding_service(self, reference, service):
        self.subs[reference] = self.server.add_middleware(
            service, reference.get_sort_value()
        )

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        if self.subs[reference]:
            self.subs[reference]()
            del self.subs[reference]


class SecurityTracker(ServiceTracker, IServiceTrackerListener):
    def __init__(self, ctx: IBundleContext, server: IHttpServer):
        super().__init__(self, ctx, IHttpSecurity)
        self.server = server

    def on_adding_service(self, reference, service):
        pass
        # self.server.set_security(service)

    def on_modified_service(self, reference, service):
        pass

    def on_removed_service(self, reference, service):
        # self.server.unset_security(service)
        pass


class ServerService:
    def __init__(self, ctx: IBundleContext, props: t.Dict[str, str]):
        self.ctx = ctx
        self.props = props
        self.engine_factory = ServerEngineFactory()
        self.reg = None
        self.servers: dict[str, t.Any] = {}
        self.scopes: list[str] = []

    async def open(self):
        if "host" in self.props and "port" in self.props:
            await self.updated(
                "default", self.props, self.props.get("scope", "default")
            )
        else:
            self.reg = await self.ctx.register_service(
                IConfigurationManagedFactory, self, {SERVICE_FACTORY_PID: "http-server"}
            )

    async def close(self):
        if self.reg:
            await self.reg.unregister()
            self.reg = None
        for pid in list(self.servers.keys()):
            await self._remove(pid)

    async def updated(self, pid: str, props=None, scope=None):
        scope = scope if scope is not None else props.get("scope", "default")
        if scope in self.scopes:
            logger.error("Server with scope: %s already running", scope)
            return

        await self._remove(pid)

        host, port = props["host"], int(props["port"])
        self.scopes.append(scope)
        server = HttpServer(self.engine_factory, host, port)
        try:
            logger.info("Start http server http://%s:%d (scope=%s)", host, port, scope)
            await server.open()
        except OSError as error:
            logger.error("Failed to create HTTP server at port %d: %s", port, error)
        else:
            trackers = [
                MiddlewareTracker(self.ctx, server, scope),
                RouteTracker(self.ctx, server, scope),
            ]
            for tracker in trackers:
                await tracker.open()
            self.servers[pid] = (server, trackers, scope)

    async def deleted(self, pid: str):
        await self._remove(pid)

    async def _remove(self, pid):
        if pid in self.servers:
            server, trackers, scope = self.servers[pid]
            del self.servers[pid]
            for track in trackers:
                await track.close()
            await server.close()
            self.scopes.remove(scope)
