import os
import typing as t

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.history import FileHistory


class Session:
    def __init__(self):
        file_path = os.path.abspath(".odsshistory")
        self.prompt_session = PromptSession(history=FileHistory(file_path))

    def write_line(self, data: str, flush=True) -> t.Awaitable[None]:
        self.write(data)
        if data[-1] != "\n":
            self.write("\n")
        if flush:
            self.flush()

    def write(self, data) -> t.Awaitable[None]:
        with patch_stdout():
            self.prompt_session.output.write(data)

    def flush(self) -> t.Awaitable[None]:
        with patch_stdout():
            self.prompt_session.output.flush()

    async def readline(self) -> t.Awaitable[str]:
        with patch_stdout():
            return await self.prompt_session.prompt_async("$> ", refresh_interval=0.5)
