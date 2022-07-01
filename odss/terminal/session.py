import os
import typing as t

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout


class ShellCompleter:
    def __init__(self, completer):
        self.completer = completer

    def get_completions(self, document, event):
        word_before_cursor = document.text_before_cursor.lstrip()
        commands = self.completer.get_completions(word_before_cursor)
        for name in commands:
            if name.startswith(word_before_cursor):
                yield Completion(
                    name,
                    -len(word_before_cursor),
                )


class Session:
    def __init__(self, completer):
        file_path = os.path.abspath(".odsshistory")
        self.prompt_session = PromptSession(
            history=FileHistory(file_path),
            auto_suggest=AutoSuggestFromHistory(),
            completer=ShellCompleter(completer),
            complete_in_thread=True,
        )

    def write_line(self, data: str, flush=True) -> None:
        self.write(data)
        if data[-1] != "\n":
            self.write("\n")
        if flush:
            self.flush()

    def write(self, data) -> None:
        with patch_stdout():
            self.prompt_session.output.write(data)

    def flush(self) -> None:
        with patch_stdout():
            self.prompt_session.output.flush()

    async def readline(self) -> t.Awaitable[str]:
        return await self.prompt("$> ")

    async def prompt(self, message) -> t.Awaitable[str]:
        with patch_stdout():
            return await self.prompt_session.prompt_async(
                message,
                # completer=self.completer,
                refresh_interval=0.5,
                # set_exception_handler=False,
                # handle_sigint=False
            )
