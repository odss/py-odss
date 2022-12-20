import logging
import typing as t

from odss.common import (
    SERVICE_FACTORY_PID,
    IBundleContext,
    IServiceReference,
    IServiceTrackerListener,
    IConfigurationManagedFactory,
    ServiceTracker,
)
from odss.http.common import (
    IHttpServer,
    IHttpServerEngineFactory,
    IHttpSecurity,
    IHttpRouteService,
    IHttpMiddlewareService,
)

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
        query = {"scope": scope} if scope else None
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
        query = {"scope": scope} if scope else None
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


class ServerEngineFactoryTracker(ServiceTracker, IServiceTrackerListener):
    def __init__(self, ctx: IBundleContext, props: t.Dict[str, str]):
        super().__init__(self, ctx, IHttpServerEngineFactory)
        self.ctx = ctx
        self.props = props
        self.engine_factory = None
        self.reg = None
        self.servers: t.Dict[str, t.Any] = {}

    async def on_adding_service(self, reference, service):
        if self.engine_factory:
            logger.warning("Server engine already registered")
            return

        self.engine_factory = service
        if "host" in self.props and "port" in self.props:
            await self.updated("default", self.props, self.props.get("scope", ""))
        else:
            self.reg = await self.ctx.register_service(
                IConfigurationManagedFactory, self, {SERVICE_FACTORY_PID: "http-server"}
            )

    def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        if self.reg:
            await self.reg.unregister()
            self.reg = None

        if self.engine_factory:
            pids = list(self.servers.keys())
            for pid in pids:
                await self._close(pid)
            self.engine_factory = None

    async def updated(self, pid: str, props=None, scope=None):
        await self._close(pid)

        host, port = props["host"], int(props["port"])
        scope = scope if scope is not None else props.get("scope")
        if self.engine_factory:
            server = HttpServer(self.engine_factory, host, port)
            trackers = [
                MiddlewareTracker(self.ctx, server, scope),
                RouteTracker(self.ctx, server, scope),
            ]
            await server.open()
            for tracker in trackers:
                await tracker.open()
            self.servers[pid] = (server, trackers)

    async def deleted(self, pid: str):
        self._close(pid)

    async def _close(self, pid):
        if pid in self.servers:
            server, trackers = self.servers[pid]
            del self.servers[pid]
            for track in trackers:
                await track.close()
            await server.close()
