import time

from ghoshell.messages import Output, Text
from ghoshell.shell_protos.baidu_speech import BaiduSpeechShell
from ghoshell.shell_protos.sphero.runtime import SpheroBoltRuntime, SpheroCommandMessage


class SpheroBoltShell(BaiduSpeechShell):
    """
    实现一个基于 LLM 的 Sphero 的自然语言交互界面.
    Shell 的任务包括:
    - 驱动, 控制 Sphero
    - 支持 文字/语音 两种方式获取用户的指令, 并发送给 Ghost
    - 接受到 Ghost 下发的指令, 用来驱动 Sphero 的行为.
    - 实现 DSL 来方便控制 Sphero, 而且是实时的.
    - 要求 Ghost 需要具备学习指令的能力.
    """
    _sphero_runtime: SpheroBoltRuntime | None = None

    def deliver(self, _output: Output) -> None:

        commands = SpheroCommandMessage.read(_output.payload)
        if commands is not None:
            self._sphero_runtime.set_cmd_message(commands)
        super().deliver(_output)
        return None

    def _output_text(self, text: Text) -> None:
        self._print_text(text)

    def run_as_app(self) -> None:
        self._console.print("bootstrap sphero bolt...")
        self._sphero_runtime = SpheroBoltRuntime(
            self._speak_text,
            self._console,
            0.1,
        )
        self._sphero_runtime.run()
        count = 0
        while count < 20:
            if self._sphero_runtime.ready:
                break
            time.sleep(1)
        if not self._sphero_runtime.ready:
            self._console.print("failed to boot sphero")
            exit(0)
        # use Thread to run sphero BOLT
        super().run_as_app()

    def _close(self) -> None:
        if self._sphero_runtime is not None:
            self._sphero_runtime.close()
        super()._close()
