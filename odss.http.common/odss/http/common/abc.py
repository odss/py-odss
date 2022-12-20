import abc
import typing as t
import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class RouteInfo:
    name: str
    method: str
    path: str
    handler: t.Callable
    settings: dict[str, t.Any] = dc.field(default_factory=dict)

    @staticmethod
    def get(name: str, path: str, handler: t.Callable) -> "RouteInfo":
        return RouteInfo(name, "GET", path, handler)


class IHttpServer:
    @abc.abstractmethod
    def register_route(self, route: RouteInfo) -> t.Callable[[], None]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_middleware(
        self, middleware: t.Callable, priority: tuple[int]
    ) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpRouter:
    @abc.abstractmethod
    def register_route(self, route: RouteInfo) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpServerEngine:
    @abc.abstractmethod
    def add_middleware(
        self, middleware: t.Callable, priority: tuple[int]
    ) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpServerEngineFactory:
    @abc.abstractmethod
    def create(self, host: str, port: str) -> IHttpServerEngine:
        raise NotImplementedError()


class Request:
    pass


class IHttpContext(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def request(self) -> Request:
        raise NotImplementedError()

    @abc.abstractmethod
    def response(
        self,
        body,
        status: int = 200,
        *,
        headers: dict | None = None,
        content_type: str | None = None,
        charset: str | None = None
    ):
        raise NotImplementedError()

    @abc.abstractmethod
    def json_response(
        self, data: t.Any, status: int = 200, *, headers: t.Optional[t.Dict] = None
    ):
        raise NotImplementedError()


_Handler = t.Callable[[Request], t.Awaitable[t.Any]]
_Middleware = t.Callable[[Request, _Handler], t.Awaitable[t.Any]]


class IHttpService:
    pass


class IHttpRouteService:
    pass


class IHttpMiddlewareService:
    pass


@dc.dataclass(frozen=True, slots=True)
class AuthInfo:
    identifier: str | None = None
    is_authenticated: bool | None = True
    is_anonymous: bool | None = False

    @staticmethod
    def create_anonymous():
        return AuthInfo(is_anonymous=True, is_authenticated=False)


class IHttpSecurityPolicy(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def identify(self, ctx: IHttpContext) -> str:
        """Return the identity` of the current client."""

    @abc.abstractmethod
    def authenticated(self, ctx: IHttpContext) -> AuthInfo:
        """Return a client info identifying"""

    @abc.abstractmethod
    def permits(self, ctx: IHttpContext, permission: str) -> bool:
        """Check user permission"""

    @abc.abstractmethod
    def remember(self, ctx: IHttpContext, identity: str, **kw) -> None:
        ...

    @abc.abstractmethod
    def forget(self, ctx: IHttpContext, **kw) -> None:
        ...


class IHttpSecurity:
    @abc.abstractmethod
    async def remember(self, ctx: IHttpContext, identity: str) -> None:
        ...

    @abc.abstractmethod
    async def forget(self, ctx: IHttpContext, identity: str) -> None:
        ...

    @abc.abstractmethod
    async def permits(self, ctx: IHttpContext, resource: str):
        ...
