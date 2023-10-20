import abc
import typing as t

from .consts import SHELL_COMMAND_HANDLER


class IShellStream:
    def write_line(self, line: str):
        pass


class ShellService(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def register_command(
        self, name: str, handler: t.Callable, namespace: str | None = None
    ) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def unregister_command(self, name: str, namespace: str | None = None) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_namespaces(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_commands(self, namespace: str | None = None):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_all_commands(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def execute(self, cmd_line: str, stream: IShellStream):
        raise NotImplementedError()


class ShellCommands:
    pass


def command(name: str | None = None, namespace: str | None = None, **attrs):
    def command_decorator(fn):
        attrs["name"] = name or fn.__name__.lower().replace("_", "-")
        attrs["namespace"] = namespace or ""
        setattr(fn, SHELL_COMMAND_HANDLER, attrs)
        return fn

    return command_decorator
