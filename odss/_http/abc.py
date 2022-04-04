import abc
import typing as t


class IHttpServer:
    @abc.abstractmethod
    def register_route(
        self, methods: t.List[str], path: str, name: str, handler: t.Callable
    ) -> t.Callable[[], None]:
        raise NotImplementedError()

    @abc.abstractmethod
    def add_middleware(
        self, middleware: t.Callable, priority: t.Tuple[int] = None
    ) -> t.Callable[[], None]:
        raise NotImplementedError()


class IHttpRequest:
    pass


class IHttpContext(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def request(self) -> IHttpRequest:
        raise NotImplementedError()

    @abc.abstractmethod
    def response(
        self,
        body,
        status: int = 200,
        *,
        headers: t.Optional[t.Dict] = None,
        content_type: str = None,
        charset: t.Optional[str] = None
    ):
        raise NotImplementedError()

    @abc.abstractmethod
    def json_response(
        self, data: t.Any, status: int = 200, *, headers: t.Optional[t.Dict] = None
    ):
        raise NotImplementedError()


_Handler = t.Callable[[IHttpRequest], t.Awaitable[t.Any]]
_Middleware = t.Callable[[IHttpRequest, _Handler], t.Awaitable[t.Any]]

# IHttpService = "odss.service.http"
# IHttpRouteService = "odss.service.http.route"
# IHttpMiddlewareService = "odss.service.http.middleware"


class IHttpService:
    pass


class IHttpRouteService:
    pass


class IHttpMiddlewareService:
    pass
