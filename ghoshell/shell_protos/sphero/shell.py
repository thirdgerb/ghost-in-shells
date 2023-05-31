import uuid
from typing import Optional

from rich.console import Console

from ghoshell.container import Container
from ghoshell.messages import Input, Output
from ghoshell.messages import Text
from ghoshell.shell_fmk import ShellKernel


class SpheroShell(ShellKernel):
    """
    实现一个基于 LLM 的 Sphero 的自然语言交互界面.
    Shell 的任务包括:
    - 驱动, 控制 Sphero
    - 支持 文字/语音 两种方式获取用户的指令, 并发送给 Ghost
    - 接受到 Ghost 下发的指令, 用来驱动 Sphero 的行为.
    - 实现 DSL 来方便控制 Sphero, 而且是实时的.
    - 要求 Ghost 需要具备学习指令的能力.
    """

    def __init__(self, container: Container, config_path: str, runtime_path: str):
        self._console = Console()
        self.session_id = str(uuid.uuid4().hex)
        self.user_id = str(uuid.uuid4().hex)
        self._talking = False
        super().__init__(container, config_path, runtime_path)

    def deliver(self, _output: Output) -> None:
        pass

    def on_event(self, e: str) -> Optional[Input]:
        content = e.strip()
        if content == "/exit":
            self._console.print("bye!")
            exit(0)

        trace = dict(
            clone_id=self.session_id,
            session_id=self.session_id,
            shell_id=self.session_id,
            shell_kind="audio_shell",
            subject_id=self.user_id,
        )
        text = Text(content=content)
        return Input(
            mid=uuid.uuid4().hex,
            payload=text.as_payload_dict(),
            trace=trace,
        )

    def run_as_app(self) -> None:
        pass
