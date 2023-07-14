import asyncio
import uuid
from typing import List, Optional, ClassVar

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from rich.console import Console
from rich.markdown import Markdown

from ghoshell.container import Container
from ghoshell.framework.shell import ShellKernel
from ghoshell.framework.shell import ShellOutputPipe
from ghoshell.ghost import Ghost
from ghoshell.messages import *


class ConsoleShell(ShellKernel):
    KIND: ClassVar[str] = "console"

    providers = []

    # 初始化流程
    bootstrapping = []

    # 输入处理
    input_middlewares = [
        # InputTestMiddleware()
    ]

    # 输出处理
    output_middlewares: ClassVar[List[ShellOutputPipe]] = [
    ]

    def __init__(self, container: Container, config_path: str, runtime_path: str):
        # message_queue = ghost
        ghost = container.force_fetch(Ghost)
        self._session_id = str(uuid.uuid4().hex)
        self._user_id = str(uuid.uuid4().hex)
        self._app = Console()
        self._ghost = ghost
        self._session: PromptSession | None = None
        super().__init__(container, config_path, runtime_path)

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
            background_task = asyncio.create_task(self.listen_async_output())
            try:
                await self._prompt_loop()
            finally:
                background_task.cancel()
            self._app.print("Quitting event loop. Bye.")

    async def _prompt_loop(self):
        session = PromptSession("\n\n<<< ", )
        self._session = session
        bindings = KeyBindings()

        self.tick("")
        while True:
            try:
                event = await session.prompt_async(multiline=False, key_bindings=bindings)
                self.tick(event)
            except (EOFError, KeyboardInterrupt):
                self._app.print(f"quit!!")
                exit(0)

    def on_event(self, prompt: str) -> Optional[Input]:
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

    def deliver(self, _output: Output) -> None:
        signal = Signal.read(_output.payload)
        if signal is not None:
            self._on_signal(signal)
            return
        text = Text.read(_output.payload)
        if text is not None:
            if text.markdown:
                self._app.print(self._markdown_output(text.content))
            else:
                self._app.print(text.content)

        err = ErrMsg.read(_output.payload)
        if err is not None:
            where = ""
            if err.at:
                where = f"at {err.at}"
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
