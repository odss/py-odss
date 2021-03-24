import pytest

from odss.shell.decorators import command
from odss.shell.shell import Shell

pytestmark = pytest.mark.asyncio


def command_handler():
    pass


def test_registration_command(shell):
    assert shell.register_command("test", command_handler), "Command not registered"
    assert not shell.register_command(
        "test", command_handler
    ), "Command registered twice"


def test_invalid_registration_command(shell):
    for invalid_name in ("", " ", None):
        with pytest.raises(AssertionError):
            shell.register_command(invalid_name, command_handler),

    with pytest.raises(AssertionError):
        shell.register_command("test", None)

    with pytest.raises(AssertionError):
        shell.register_command("test", 123)


def test_unregister_command(shell):
    assert not shell.unregister_command("test"), "Not exists command"
    assert not shell.unregister_command("test", "ns"), "Not exists command"

    shell.register_command("test", command_handler, "ns")

    assert len(shell.get_namespaces()) == 1

    assert not shell.unregister_command("test"), "Not unregister command"
    assert shell.unregister_command("test", "ns"), "Not unregister command"


async def test_execute_incorrect_commands(shell, shell_session):
    with shell_session:
        assert not await shell.execute(shell_session, "test'")
        assert shell_session.output == "Error reading line: No closing quotation\n"

    with shell_session:
        assert not await shell.execute(shell_session, "test")
        assert "Unknown command: test" in shell_session.output

    with shell_session:
        assert not await shell.execute(shell_session, "ns.test")
        assert "Unknown command: ns.test" in shell_session.output


async def test_execute_commands(shell, shell_session):
    def command_handler(session, *args, **kwargs):
        session.write_line("run")

    shell.register_command("test", command_handler)

    assert await shell.execute(shell_session, "test")
    assert shell_session.output == "run\n"


class Commands:
    @command()
    def test():
        return "test"

    @command("foo")
    def bar():
        return "foo/bar"

    @command(alias="?")
    def help():
        return "help/?"

    @command("help", namespace="ns")
    def ns_help():
        return "ns.help"


def test_bind_handler(shell):
    commands = Commands()

    shell.bind_handler(commands)

    assert shell.get_namespaces() == ["ns"]

    names = shell.get_commands()
    assert len(names) == 4
    assert names == ["?", "foo", "help", "test"]

    names = shell.get_commands("ns")
    assert len(names) == 1
    assert names == ["help"]

    names = shell.get_all_commands()
    assert len(names) == 5
    assert names == ["?", "foo", "help", "ns.help", "test"]

    shell.unbind_handler(commands)

    assert len(shell.get_namespaces()) == 0
    assert len(shell.get_commands()) == 0
