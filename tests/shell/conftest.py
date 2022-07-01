import pytest

from odss.shell.shell import Shell


class TestSession:
    def __init__(self):
        # super().__init__({})
        self.stack = []
        self.output = ""
        self.buff = []

    def write(self, data: str):
        self.buff.append(data)

    def write_line(self, line: str):
        self.buff.append(f"{line}\n")
        self.flush()

    def flush(self):
        self.output += "".join(self.buff)
        self.buff = []

    def __enter__(self):
        self.stack.append((self.output, self.buff))
        self.output = ""
        self.buff = []

    def __exit__(self, _, __, ___):
        self.output, self.buff = self.stack.pop()


@pytest.fixture()
def shell_session():
    return TestSession()


@pytest.fixture()
def shell(framework):
    """
    Create shell service
    """
    return Shell(framework.get_context())
