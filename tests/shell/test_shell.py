import pytest


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


def test_unregister_command(shell):
    assert not shell.unregister_command("test"), "Not exists command"
    assert not shell.unregister_command("test", "ns"), "Not exists command"
    shell.register_command("test", command_handler, "ns")
    assert not shell.unregister_command("test"), "Not unregister command"
    assert shell.unregister_command("test", "ns"), "Not unregister command"


async def test_execute_incorrect_commands(shell, shell_session):
    assert not await shell.execute("test'", shell_session)
    assert shell_session.output == "Error reading line: No closing quotation\n"

    assert not await shell.execute("test", shell_session)
    assert shell_session.output == "Unknown command: test\n"

    assert not await shell.execute("ns.test", shell_session)
    assert shell_session.output == "Unknown command: ns.test\n"

    shell.register_command("test", 123)
    assert not await shell.execute("test", shell_session)
    assert (
        shell_session.output == "Command call problem: 'int' object is not callable\n"
    )


async def test_execute_commands(shell, shell_session):
    def command_handler(session, *args, **kwargs):
        session.write_line("run")

    shell.register_command("test", command_handler)

    assert await shell.execute("test", shell_session)
    assert shell_session.output == "run\n"


async def test_default_commands(shell, shell_session):

    with pytest.raises(KeyboardInterrupt):
        await shell.execute("exit", shell_session)
