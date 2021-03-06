import pytest

from odss.shell.shell import Shell
from odss.shell.session import Session


class TestSession(Session):
    def __init__(self):
        super().__init__()
        self.output = ""
        self.buff = []

    def write(self, data: str):
        self.buff.append(data)

    def flush(self):
        self.output = "".join(self.buff)
        self.buff = []


@pytest.fixture()
def shell_session():
    return TestSession()


@pytest.fixture()
def shell(framework):
    """
    Create shell service
    """
    return Shell(framework.get_context())


@pytest.fixture()
def service_shell(framework):
    """
    Create shell service
    """
    return ServiceShell(framework.get_context())
