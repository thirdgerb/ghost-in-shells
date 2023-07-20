from __future__ import annotations

import asyncio
import uuid
from typing import Optional, ClassVar, List

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from rich.console import Console
from rich.markdown import Markdown

from ghoshell.container import Container
from ghoshell.container import Provider
from ghoshell.framework.shell import ShellKernel
from ghoshell.framework.shell import ShellOutputMdw, ShellInputMdw, ShellBootstrapper
from ghoshell.ghost import Ghost
from ghoshell.messages import *


class ConsoleShell(ShellKernel):
    KIND: ClassVar[str] = "console"

    def __init__(self, container: Container, config_path: str, runtime_path: str):
        # message_queue = ghost
        ghost = container.force_fetch(Ghost)
        self._session_id = str(uuid.uuid4().hex)
        self._user_id = str(uuid.uuid4().hex)
        self._app = Console()
        self._ghost = ghost
        self._session: PromptSession | None = None
        super().__init__(container, config_path, runtime_path)

    def get_bootstrapper(self) -> List[ShellBootstrapper]:
        return []

    def get_providers(self) -> List[Provider]:
        return []

    def get_input_mdw(self) -> List[ShellInputMdw]:
        return []

    def get_output_mdw(self) -> List[ShellOutputMdw]:
        return []

    def _welcome(self) -> None:
        self._app.print(Markdown("""
----
# Console Demo

print "/exit" to quit

log:
- 2023-4-28: achieve "hello world"

----
"""))

    def kind(self) -> str:
        return "command_shell"

    def run_as_app(self):
        self._welcome()
        asyncio.run(self._main())

    async def _main(self):
        with patch_stdout(raw=True):
            await self._prompt_loop()
            self._app.print("Quitting event loop. Bye.")

    async def _prompt_loop(self):
        session = PromptSession("\n\n<<< ", )
        self._session = session
        bindings = KeyBindings()

        self.handle("")
        while True:
            try:
                event = await session.prompt_async(multiline=False, key_bindings=bindings)
                self._app.print(Markdown("\n----\n"))
                self.handle(event)
            except (EOFError, KeyboardInterrupt):
                self._app.print(f"quit!!")
                exit(0)

    def parse_event(self, prompt: str) -> Optional[Input]:
        if prompt == "/exit":
            self._quit()
        prompt = prompt.strip()
        trace = dict(
            clone_id=self._session_id,
            session_id=self._session_id,
            shell_id=self._session_id,
            shell_kind=self.kind(),
            subject_id=self._user_id,
        )
        text = Text(content=prompt)
        return Input(
            mid=uuid.uuid4().hex,
            payload=text.as_payload_dict(),
            trace=trace,
        )

    def _quit(self):
        if self._session is not None:
            # todo: close?
            pass
        self._app.print("Exit, Bye!")
        exit(0)

    def _on_signal(self, signal: Signal):
        if signal.code == signal.QUIT_CODE:
            self._quit()

    def output(self, _output: Output, _input: Input) -> None:
        signal = Signal.read(_output.payload)
        if signal is not None:
            self._on_signal(signal)
            return
        text = Text.read(_output.payload)
        if text is not None:
            if text.markdown:
                self._app.print(self._markdown_output(text.content))
            else:
                self._app.print("\n\n" + text.content)

        err = ErrMsg.read(_output.payload)
        if err is not None:
            where = ""
            err_info = self._markdown_output(
                f"# Error Occur {err.errcode}\n\n{err.errmsg} {where}\n\n{err.stack_info}")
            self._app.print(err_info)

        signal = Signal.read(_output.payload)
        if signal is not None and signal.code == signal.QUIT_CODE:
            self._quit()

    def _markdown_output(self, text: str) -> Markdown:
        lines = text.split("\n\n")
        result = ["----"]
        for line in lines:
            # line = "\n\n".join(line.split("\n"))
            result.append(line)
        return Markdown("\n\n".join(result))

    def deliver(self, _input: Input) -> List[Output] | None:
        return self._ghost.respond(_input)
