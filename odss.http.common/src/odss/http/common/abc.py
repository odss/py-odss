import io
import abc
import dataclasses as dc
import typing as t

from yarl import URL
from multidict import CIMultiDictProxy, MultiDictProxy


class FileField(metaclass=abc.ABCMeta):
    name: str
    filename: str
    file: io.BufferedReader
    content_type: str
    headers: "CIMultiDictProxy[str]"


class Request(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def is_secure(self) -> bool:
        """If is secure request"""
        raise NotImplemented

    @property
    @abc.abstractmethod
    def scheme(self) -> str:
        """
        Return scheme or request.

        'http' or 'https'
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def method(self) -> str:
        """
        HTTP method.

        Values: 'GET', 'POST', 'PUT', 'UPDATE', 'HEAD', "DELETE', 'OPTIONS', 'TRACE'.
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def host(self) -> str:
        """Hostname of the request."""
        raise NotImplemented

    @property
    @abc.abstractmethod
    def remote(self) -> str | None:
        """Remote IP of client"""
        raise NotImplemented

    @property
    @abc.abstractmethod
    def url(self) -> URL:
        raise NotImplemented

    @property
    @abc.abstractmethod
    def path(self) -> str:
        """
        URL including path without host or scheme.

        E.g., ``/blog/post``
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def path_qs(self) -> str:
        """
        URL including path and query string.

        E.g, /blog/post?id=8
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def query(self) -> MultiDictProxy[str]:
        """
        Query as dict like object.
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def query_string(self) -> str:
        """
        Query string in the URL.

        E.g., id=8
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def params(self) -> dict[str, str]:
        raise NotImplemented

    @property
    @abc.abstractmethod
    def headers(self) -> CIMultiDictProxy[str]:
        """
        Return request headers.

        A case-insensitive multidict read-only of headers.
        """
        raise NotImplemented

    @property
    @abc.abstractmethod
    def cookies(self) -> t.Mapping[str, str]:
        """
        Return request cookies.

        A read-only dict like object.
        """
        raise NotImplemented

    @abc.abstractmethod
    async def read(self) -> bytes:
        """
        Read request body
        """
        raise NotImplemented

    @abc.abstractmethod
    async def text(self) -> str:
        """
        Return request body as text using charset to encoding.
        """
        raise NotImplemented

    @abc.abstractmethod
    async def json(self) -> t.Any:
        """
        Return request body as json
        """
        raise NotImplemented

    @abc.abstractmethod
    async def multipart(self) -> t.Any:
        """
        @TODO
        """
        raise NotImplemented

    @abc.abstractmethod
    async def post(self) -> MultiDictProxy[str | bytes | FileField]:
        """Return POST parameters."""
        raise NotImplemented

    def __getitem__(self, key: str) -> t.Any:
        pass

    def __setitem__(self, key: str, value: t.Any):
        pass
    
    @property
    @abc.abstractmethod
    def content_type(self) -> str:
        raise NotImplemented

    @property
    @abc.abstractmethod
    def charset(self) -> str | None:
        raise NotImplemented




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


class IHttpServer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_route(self, route: RouteInfo) -> t.Callable[[], None]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_middleware(
        self, middleware: t.Callable, priority: tuple[int, int]
    ) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpRouter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def register_route(self, route: RouteInfo) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpServerEngine(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_middleware(
        self, middleware: t.Callable, priority: tuple[int, int]
    ) -> t.Callable[[], None]:
        raise NotImplementedError()


HttpServerHandler = t.Callable[[Request], t.Awaitable[t.Any]]
HttpServerEngineRequestHandler = t.Callable[[HttpServerHandler, Request], t.Awaitable[t.Any]]

class IHttpServerEngineFactory(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create(self, request_handler: HttpServerEngineRequestHandler, host: str, port: int) -> IHttpServerEngine:
        raise NotImplemented


_Handler = t.Callable[[Request], t.Awaitable[t.Any]]
_Middleware = t.Callable[[Request, _Handler], t.Awaitable[t.Any]]


class IHttpService:
    pass


class IHttpRouteService:
    pass


class IHttpMiddlewareService:
    pass


class ICsrf(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def token(self, request: Request) -> str:
        pass

    @abc.abstractmethod
    def verify(self, token: str) -> bool:
        pass

    @abc.abstractmethod
    def regenerate(self):
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
    def identify(self, request: Request) -> str:
        """Return the identity` of the current client."""

    @abc.abstractmethod
    def authenticated(self, request: Request) -> AuthInfo:
        """Return a client info identifying"""

    @abc.abstractmethod
    def permits(self, request: Request, permission: str) -> bool:
        """Check user permission"""

    @abc.abstractmethod
    def remember(self, request: Request, identity: str, **kw) -> None:
        ...

    @abc.abstractmethod
    def forget(self, request: Request, **kw) -> None:
        ...


class IHttpSecurity:
    @abc.abstractmethod
    async def remember(self, request: Request, identity: str) -> None:
        ...

    @abc.abstractmethod
    async def forget(self, request: Request, identity: str) -> None:
        ...

    @abc.abstractmethod
    async def permits(self, request: Request, resource: str):
        ...
