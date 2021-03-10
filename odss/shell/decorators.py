from .consts import ODSS_SHELL_COMMAND_HANDLER


def command(name: str = None, namespace: str = None, **attrs):
    def decorator(fn):
        attrs["name"] = name or fn.__name__.lower().replace("_", "-")
        attrs["namespace"] = namespace or ""
        setattr(fn, ODSS_SHELL_COMMAND_HANDLER, attrs)
        return fn

    return decorator
