import inspect
import typing as t

from .consts import ODSS_HTTP_HANDLER, ODSS_HTTP_VIEW

RouteOptions = t.TypedDict(
    "RouteOptions",
    {"method": str, "path": str, "name": str, "settings": dict[str, t.Any]},
)

ViewOptions = t.TypedDict("ViewOptions", {"prefix": str})

F = t.TypeVar("F", bound=t.Callable[..., t.Any])


def _create_route_decorator(
    method: str,
) -> t.Callable:
    def route(path: str = "", **settings):
        settings["method"] = method.upper()
        settings["path"] = path

        def route_decorator(fn):
            name = settings.get("name")
            settings["name"] = (
                (name if name else fn.__qualname__).replace(">", "").replace("<", "")
            )
            setattr(fn, ODSS_HTTP_HANDLER, settings)
            return fn

        return route_decorator

    return route


HandlerInfo = t.Tuple[t.Callable, t.Dict[str, t.Any]]


def extract_route(handler: t.Callable) -> dict[str, t.Any]:
    return getattr(handler, ODSS_HTTP_HANDLER)


def extract_view_handlers(obj: t.Any) -> t.Generator[HandlerInfo, None, None]:
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


class route:
    def __2init__(self, method: str, path: str, *, name: str | None = None, **settings):
        settings["method"] = method.upper()
        settings["path"] = path
        settings["name"] = name
        self.settings = settings

    def __call__(self, handler):
        name = self.settings["name"]
        if not name:
            name = handler.__qualname__.lower().replace(">", "").replace("<", "")
        self.settings["name"] = name
        setattr(handler, ODSS_HTTP_HANDLER, self.settings)
        return handler

    @staticmethod
    def view(prefix: str = ""):
        def view_wrapper(view):
            setattr(view, ODSS_HTTP_VIEW, {"prefix": prefix})
            return view

        return view_wrapper

    get = _create_route_decorator("GET")
    post = _create_route_decorator("POST")
    delete = _create_route_decorator("DELETE")
    put = _create_route_decorator("PUT")
    patch = _create_route_decorator("PATCH")
    option = _create_route_decorator("OPTIONS")
    head = _create_route_decorator("HEAD")
