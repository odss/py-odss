from .consts import ODSS_HTTP_ROUTE_HANDLER


def _create_route_decorator(methods: str):
    def route(path: str, name: str = None, **options):
        def route_decorator(fn):
            options["path"] = path
            options["methods"] = methods
            options["name"] = name if name else fn.__qualname__
            setattr(fn, ODSS_HTTP_ROUTE_HANDLER, options)
            return fn

        return route_decorator

    return route


class route:
    def __init__(self, path: str, methods: str = "*", name: str = None, **options):
        options["name"] = name
        options["path"] = path
        options["methods"] = methods
        self.options = options

    def __call__(self, fn):
        if not self.options["name"]:
            self.options["name"] = fn.__qualname__.lower()
        setattr(fn, ODSS_HTTP_ROUTE_HANDLER, self.options)
        return fn


get = _create_route_decorator("GET")
post = _create_route_decorator("POST")
delete = _create_route_decorator("DELETE")
put = _create_route_decorator("PUT")
patch = _create_route_decorator("PATCH")
option = _create_route_decorator("OPTIONS")
head = _create_route_decorator("HEAD")
