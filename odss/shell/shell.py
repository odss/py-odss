import asyncio
import collections
import inspect
import io
import logging
import shlex
import sys
import traceback
import typing as t

from .consts import DEFAULT_NAMESPACE, ODSS_SHELL_COMMAND_HANDLER
from .decorators import command

logger = logging.getLogger(__name__)


class OutputStream:
    pass


class Shell:
    def __init__(self, ctx, bind_basic=False):
        self.ctx = ctx
        self._commands = collections.defaultdict(dict)
        self._handlers = collections.defaultdict(list)

        if bind_basic:
            self.bind_handler(self)

    @command("help", alias="?")
    def print_help(self, session: OutputStream, name: str = None) -> None:
        """
        Prints info about all available commands.
        """
        if name:
            if name in self._commands:
                self._print_namespace_help(session, name)
            else:
                namespace, cmdname = self._parse_command_name(name)
                self._print_command_help(session, namespace, name)
        else:
            namespaces = list(self._commands.keys())
            namespaces.remove(DEFAULT_NAMESPACE)
            namespaces.sort()
            namespaces.append(DEFAULT_NAMESPACE)
            for namespace in namespaces:
                self._print_namespace_help(session, namespace)

    def _print_command_help(self, session: OutputStream, namespace: str, name: str):
        command = self._commands[namespace][name]
        args, doc = _get_command_info(command)
        sargs = ", ".join(args[1:])
        session.write_line(f"- {name:10} {sargs:<15} {doc}")

    def _print_namespace_help(self, session, namespace):
        session.write_line(f"[{namespace}]")
        for name in sorted(self._commands[namespace].keys()):
            self._print_command_help(session, namespace, name)

    @command(alias="exit")
    async def quit(self, session: OutputStream):
        """
        Shutdown framework
        """
        session.write_line("Bye...")

        def shutdown():
            framework = self.ctx.get_framework()
            asyncio.create_task(framework.stop())

        asyncio.get_event_loop().call_soon(shutdown)

    def bind_handler(self, handler: t.Any):
        """
        Bind handler
        """
        if handler in self._handlers:
            logger.warning("Handler already register: %s", handler)
            return False

        commands = []
        for method, attrs in _extract_command_handlers(handler):
            name = attrs["name"]
            namespace = attrs.get("namespace") or DEFAULT_NAMESPACE
            alias = attrs.get("alias", [])

            self.register_command(name, method, namespace)
            commands.append((name, namespace))

            if not isinstance(alias, (tuple, list)):
                alias = [alias]
            for name in alias:
                self.register_command(name, method, namespace)
                commands.append((name, namespace))

        self._handlers[handler] = commands
        return True

    def unbind_handler(self, handler: t.Any):
        if handler not in self._handlers:
            logger.warning("Handler not found: %s", handler)
            return False

        for name, namespace in self._handlers[handler]:
            self.unregister_command(name, namespace)

        del self._handlers[handler]

        return True

    def register_command(
        self, name: str, handler: t.Callable, namespace: str = DEFAULT_NAMESPACE
    ) -> bool:
        name = (name or "").strip().lower()
        namespace = namespace.strip().lower()

        assert name, "No command name"
        assert namespace, "No command namespace"
        assert handler, f"No command handler for {namespace}.{name}"
        assert callable(
            handler
        ), f"Expected callable command handler for {namespace}.{name}"
        lname = name if namespace == DEFAULT_NAMESPACE else f"{namespace}.{name}"
        logger.debug(f"Register command: {lname}")

        space = self._commands[namespace]
        if name in space:
            logger.error(f"Command already registered: {namespace}.{name}")
            return False

        space[name] = handler
        return True

    def unregister_command(self, name: str, namespace: str = DEFAULT_NAMESPACE) -> bool:
        name = (name or "").strip().lower()
        namespace = (namespace or "").strip().lower()

        assert name, "No command name"
        assert namespace, "No command namespace"

        if namespace in self._commands and name in self._commands[namespace]:
            del self._commands[namespace][name]
            lname = name if namespace == DEFAULT_NAMESPACE else f"{namespace}.{name}"
            logger.debug(f"Unregister command: {lname}")

            if not self._commands[namespace]:
                del self._commands[namespace]

            return True

        return False

    def unregister_commands(self, namespace: str) -> bool:
        namespace = (namespace or "").strip().lower()
        assert namespace, "No command namespace"
        logger.debug(f"Unregister commands: {namespace}.*")

        if namespace in self._commands:
            del self._commands[namespace]
            return True
        return False

    def get_namespaces(self):
        namespaces = list(self._commands.keys())
        try:
            namespaces.remove(DEFAULT_NAMESPACE)
        except ValueError:
            pass
        namespaces.sort()
        return namespaces

    def get_commands(self, namespace: str = DEFAULT_NAMESPACE):
        try:
            namespace.strip().lower()
            commands = list(self._commands[namespace].keys())
            commands.sort()
            return commands
        except KeyError:
            return []

    def get_all_commands(self):
        commands = []
        for namespace, handlers in self._commands.items():
            for name in handlers.keys():
                if namespace == DEFAULT_NAMESPACE:
                    commands.append(name)
                else:
                    commands.append(f"{namespace}.{name}")
        return sorted(commands)

    async def execute(self, cmdline: str, output: OutputStream):
        try:
            line_parts = shlex.split(cmdline, True, True)
        except ValueError as ex:
            output.write_line(f"Error reading line: {ex}")
            return False

        if not line_parts:
            return False

        args, kwargs = _build_params(line_parts[1:])
        try:
            namespace, name = self._parse_command_name(line_parts[0])
            command_handler = self._commands[namespace][name]
            result = command_handler(output, *args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                if not isinstance(result, str):
                    result = "\n".join(list(result))
                output.write_line(result)

            return True
        except Exception as ex:
            print(ex)
            # error_msg = "{0} - {1}".format(type(ex).__name__, str(ex))
            # session.write_line(error_msg)
            trace = _format_exception(sys.exc_info())
            output.write_line(trace)

        return False

    def _parse_command_name(self, name: str):
        namespace, cmdname = _split_command_name(name)
        if namespace not in self._commands:
            raise ValueError(f"Unknown command: {name}")

        if cmdname not in self._commands[namespace]:
            raise ValueError(f"Unknown command: {name}")
        return namespace, cmdname


def _format_exception(exc_info):
    sio = io.StringIO()
    type, value, tb = exc_info
    traceback.print_exception(type, value, tb, None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s


def _split_command_name(
    name: str, default_namespace=DEFAULT_NAMESPACE
) -> t.Tuple[str, str]:
    parts = name.split(".")
    if len(parts) == 1:
        return default_namespace, parts[0].lower()
    return parts[0].lower(), parts[1].lower()


def _build_params(params):
    args, kwargs = [], {}
    for param in params:
        if "=" in param:
            pos = param.find("=")
            key, value = param[:pos], param[pos + 1 :]
            kwargs[key] = value
        else:
            args.append(param)
    return args, kwargs


CommandInfo = t.Tuple[t.List[str], str]


def _get_command_info(command: t.Any) -> CommandInfo:
    args = []
    for param in inspect.signature(command).parameters.values():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            args.append(f"[**{param.name}]")
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            args.append(f"[*{param.name}]")
        else:
            arg = f"<{param.name}>"
            if param.default is not param.empty:
                if param.default is not None:
                    arg = f"{arg}={param.default}"
                arg = f"[{arg}]"
            args.append(arg)

    return args, inspect.getdoc(command) or ""


HandlerInfo = t.Tuple[str, t.Callable, t.Dict[str, t.Any]]


def _extract_command_handlers(obj: t.Any) -> HandlerInfo:
    members = inspect.getmembers(obj, inspect.isroutine)
    for name, fn in members:
        if not name.startswith("_"):
            attrs = getattr(fn, ODSS_SHELL_COMMAND_HANDLER, None)
            if attrs:
                yield fn, attrs
