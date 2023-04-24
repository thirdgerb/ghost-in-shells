from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ghoshell.ghost import Output, Input
from ghoshell.shell import ShellContext


class ConsoleContext(ShellContext):

    def __init__(self, console: Console, _input: Input):
        self.console = console
        self._input = _input

    def input(self) -> Input:
        return Input(**self._input.dict())

    def send(self, _output: Output) -> None:
        for payload in _output.payload:
            if payload.text is not None:
                text_message = payload.text
                self.console.print(Panel(Markdown(text_message.raw)))

    def finish(self) -> None:
        del self.console
