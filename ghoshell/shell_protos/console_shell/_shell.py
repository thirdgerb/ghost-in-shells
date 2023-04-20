import asyncio
import uuid
from typing import Dict, List, Optional

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from rich.console import Console

from ghoshell.ghost import Input, Ghost, Payload, TextMsg, Trace
from ghoshell.shell import ShellContext
from ghoshell.shell_fmk import InputMiddleware, OutputMiddleware
from ghoshell.shell_fmk import ShellKernel, Bootstrapper
from ghoshell.shell_protos.console_shell._context import ConsoleContext
from ghoshell.shell_protos.console_shell._input_pipes import InputTestMiddleware


class ConsoleShell(ShellKernel):
    # 初始化流程
    bootstrapping: List[Bootstrapper] = []

    # 输入处理
    input_middleware: List[InputMiddleware] = [
        InputTestMiddleware()
    ]
    # 输出处理
    output_middleware: List[OutputMiddleware] = []

    def __init__(self, ghost: Ghost | None = None):
        self.session_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.app = Console()
        self.ghost = ghost

    def kind(self) -> str:
        return "command_shell"

    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        with patch_stdout(raw=True):
            background_task = asyncio.create_task(self.async_ghost_output())
            try:
                await self._prompt_loop()
            finally:
                background_task.cancel()
            self.app.print("Quitting event loop. Bye.")

    async def _prompt_loop(self):
        session = PromptSession("\n\n<<< ", )
        bindings = KeyBindings()

        @bindings.add("c-p")
        def key_post(prompt_event):
            self.app.print(prompt_event)

        while True:
            try:
                event = await session.prompt_async(multiline=True, key_bindings=bindings)
                self.tick(event)
            except (EOFError, KeyboardInterrupt):
                self.app.print(f"quit!!")
                exit(0)

    def shell_env(self, ctx: ShellContext) -> Dict:
        return {}

    def context(self, _input: Input) -> ShellContext:
        return ConsoleContext(self.app, _input)

    def on_event(self, prompt: str) -> Optional[Input]:
        return Input(
            payload=Payload(
                id=str(uuid.uuid4()),
                text=TextMsg(raw=prompt)
            ),
            trace=Trace(
                clone_id=self.session_id,
                session_id=self.session_id,
                shell_id=self.session_id,
                shell_kind=self.kind(),
                subject_id=self.user_id,
            )
        )

    def connect(self, _input: Input | None) -> Ghost:
        pass
