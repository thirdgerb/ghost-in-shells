import asyncio
import uuid
from typing import List, Optional, ClassVar

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from rich.console import Console
from rich.markdown import Markdown

from ghoshell.container import Container
from ghoshell.ghost import Ghost
from ghoshell.messages import *
from ghoshell.shell import Messenger
from ghoshell.shell_fmk import InputMiddleware, OutputMiddleware
from ghoshell.shell_fmk import ShellKernel, Bootstrapper
from ghoshell.shell_fmk import SyncGhostMessenger, MessageQueue


class ConsoleShell(ShellKernel):
    KIND: ClassVar[str] = "console"

    # 初始化流程
    bootstrapping: ClassVar[List[Bootstrapper]] = []

    # 输入处理
    input_middlewares: ClassVar[List[InputMiddleware]] = [
        # InputTestMiddleware()
    ]

    # 输出处理
    output_middlewares: ClassVar[List[OutputMiddleware]] = [
    ]

    def __init__(self, container: Container):
        # message_queue = ghost
        shell_container = Container(container)
        ghost = container.force_fetch(Ghost)
        message_queue = container.force_fetch(MessageQueue)
        messenger = SyncGhostMessenger(ghost, queue=message_queue)

        self.session_id = str(uuid.uuid4().hex)
        self.user_id = str(uuid.uuid4().hex)
        self.app = Console()
        self.ghost = ghost
        super().__init__(shell_container, messenger)
        self._welcome()

    def _welcome(self) -> None:
        self.app.print(Markdown("""
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
        asyncio.run(self._main())

    async def _main(self):
        with patch_stdout(raw=True):
            background_task = asyncio.create_task(self.handle_async_output())
            try:
                await self._prompt_loop()
            finally:
                background_task.cancel()
            self.app.print("Quitting event loop. Bye.")

    async def _prompt_loop(self):
        session = PromptSession("\n\n<<< ", )
        bindings = KeyBindings()

        while True:
            try:
                event = await session.prompt_async(multiline=False, key_bindings=bindings)
                self.tick(event)
            except (EOFError, KeyboardInterrupt):
                self.app.print(f"quit!!")
                exit(0)

    def on_event(self, prompt: str) -> Optional[Input]:
        if prompt == "/exit":
            self.app.print("Exit, Bye!")
            exit(0)
        prompt = prompt.strip()
        trace = dict(
            clone_id=self.session_id,
            session_id=self.session_id,
            shell_id=self.session_id,
            shell_kind=self.kind(),
            subject_id=self.user_id,
        )
        text = Text(content=prompt)
        return Input(
            mid=uuid.uuid4().hex,
            payload=text.as_payload_dict(),
            trace=trace,
        )

    def deliver(self, _output: Output) -> None:
        text = Text.read(_output.payload)
        if text is not None:
            if text.markdown:
                self.app.print(self._markdown_output(text.content))
            else:
                self.app.print(text.content)

        err = Error.read(_output.payload)
        if err is not None:
            where = ""
            if err.at:
                where = f"at {err.at}"
            err_info = self._markdown_output(
                f"# Error Occur {err.errcode}\n\n{err.errmsg} {where}\n\n{err.stack_info}")
            self.app.print(err_info)

    def _markdown_output(self, text: str) -> Markdown:
        lines = text.split("\n\n")
        result = ["----"]
        for line in lines:
            # line = "\n\n".join(line.split("\n"))
            result.append(line)
        result.append("----")
        return Markdown("\n\n".join(result))

    def messenger(self, _input: Input | None) -> Messenger:
        return self._messenger
