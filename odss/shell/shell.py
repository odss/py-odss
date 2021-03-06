import abc
import asyncio
import shlex
import collections
import logging
import typing as t


logger = logging.getLogger(__name__)


DEFAULT_NAMESPACE = "default"


class CommandContext:
    pass

class CompleteEvent:
    pass

class Completion:
    pass

class ICommand(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def execute(self, context: CommandContext) -> None:
        pass

    async def completions(self, event: CompleteEvent) -> t.AsyncGenerator[Completion, None]:
        while False:
            yield


class Shell:
    def __init__(self, ctx=None):
        self.ctx = ctx
        self._commands = collections.defaultdict(dict)

        self.register_command("help", self.print_help)
        self.register_command("?", self.print_help)
        self.register_command("quit", self.quit)
        self.register_command("exit", self.quit)


    def register_command(self, name: str, handler: t.Any, namespace: str = DEFAULT_NAMESPACE) -> bool:
        name = (name or "").strip().lower()
        namespace = (namespace or "").strip().lower()

        assert name, "No command name"
        assert namespace, "No command namespace"
        assert handler, f"No command handler for {namespace}.{name}"

        space = self._commands[namespace]
        if name in space:
            logger.error(f'Command already registered: {namespace}.{name}')
            return False

        space[name] = handler
        return True

    def unregister_command(self, name, namespace=DEFAULT_NAMESPACE) -> bool:
        name = (name or "").strip().lower()
        namespace = (namespace or "").strip().lower()

        assert name, "No command name"
        assert namespace, "No command namespace"

        if namespace in self._commands and name in self._commands[namespace]:
                del self._commands[namespace][name]

                if not self._commands[namespace]:
                    del self._commands[namespace]

                return True

        return False

    def unregister_commands(self, namespace: str) -> bool:
        namespace = (namespace or "").strip().lower()
        assert namespace, "No command namespace"
        if namespace in self._commands:
            del self._commands[namespace]
            return True
        return False

    def get_namespaces(self):
        pass

    def get_commands(self, namespace=DEFAULT_NAMESPACE):
        pass

    async def execute(self, cmdline, session):
        try:
            line_parts = shlex.split(cmdline, True, True)
        except ValueError as ex:
            session.write_line(f"Error reading line: {ex}")
            return False

        if not line_parts:
            return False


        args, kwargs = build_params(line_parts[1:])

        error_msg = ''
        try:
            namespace, name = self._parse_command_name(line_parts[0])
            command_handler = self._commands[namespace][name]
            result = command_handler(session, *args, **kwargs)
            if asyncio.iscoroutine(result):
                await result

            return True
        except ValueError as ex:
            error_msg = str(ex)
        except TypeError as ex:
            error_msg = f"Command call problem: {ex}"
        except Exception as ex:
            error_msg = "{0} - {1}".format(type(ex).__name__, str(ex))
        finally:
            if error_msg:
                session.write_line(error_msg)
        return False

    def _parse_command_name(self, name):
        namespace, cmdname = split_command_name(name)
        if namespace not in self._commands:
            raise ValueError(f"Unknown command: {name}")

        if name not in self._commands[namespace]:
            if namespace == DEFAULT_NAMESPACE:
                name = cmdname
            raise ValueError(f"Unknown command: {name}")
        return namespace, name

    def print_help(self, session):
        pass

    def quit(self, session):
        raise KeyboardInterrupt()


def split_command_name(name: str, default_namespace=DEFAULT_NAMESPACE) -> t.Tuple[str, str]:
    parts = name.split(".")
    if len(parts) == 1:
        return default_namespace, parts[0].lower()
    return parts[0].lower(), parts[1].lower()


def build_params(params):
    args, kwargs = [], {}
    for param in params:
        if "=" in param:
            pos = param.find('=')
            key, value = param[:pos], param[pos+1:]
            kwargs[key] = value
        else:
            args.append(param)
    return args, kwargs