import abc
import typing as t

from .consts import SHELL_COMMAND_HANDLER


class IShellStream:
    def write_line(self, line: str):
        pass


class IShell(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def register_command(
        self, name: str, handler: t.Callable, namespace: str = None
    ) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def unregister_command(self, name: str, namespace: str = None) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_namespaces(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_commands(self, namespace: str = None):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_commands(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def execute(self, cmd_line: str, stream: IShellStream):
        raise NotImplementedError()


def command(name: str = None, namespace: str = None, **attrs):
    def decorator(fn):
        attrs["name"] = name or fn.__name__.lower().replace("_", "-")
        attrs["namespace"] = namespace or ""
        setattr(fn, SHELL_COMMAND_HANDLER, attrs)
        return fn

    return decorator
