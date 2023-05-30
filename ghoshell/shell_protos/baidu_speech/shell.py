import uuid
from typing import Optional

import speech_recognition as sr
from prompt_toolkit import prompt
from rich.console import Console
from rich.markdown import Markdown

from ghoshell.container import Container
from ghoshell.messages import Input, Output
from ghoshell.messages import Text
from ghoshell.shell_fmk import ShellKernel
from ghoshell.shell_protos.baidu_speech.adapter import BaiduSpeechAdapter, BaiduSpeechProvider


class BaiduSpeechShell(ShellKernel):
    """
    Shell
    """
    providers = [
        BaiduSpeechProvider(),
    ]

    def __init__(self, container: Container, config_path: str, runtime_path: str):
        self._console = Console()
        self.session_id = str(uuid.uuid4().hex)
        self.user_id = str(uuid.uuid4().hex)
        super().__init__(container, config_path, runtime_path)

    def deliver(self, _output: Output) -> None:
        text = Text.read(_output.payload)
        if text is None:
            return None
        self._markdown_print(text.content)
        self._speak(text.content)

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
        self.tick("")
        while True:
            user_input = prompt("<<< ")
            match user_input:
                case "/exit":
                    self._console.print("Bye!")
                    exit(0)
                case "":
                    self._listen()
                case _:
                    self.tick(user_input)

    def tick(self, text: str) -> None:
        self._console.print("> waiting...")
        super().tick(text)

    def _listen(self) -> None:
        adapter = self.container.force_fetch(BaiduSpeechAdapter)

        r = sr.Recognizer()
        with sr.Microphone() as source:
            self._console.print("> listening...")
            audio = r.listen(source)
        wave_data = audio.get_wav_data(convert_rate=16000)
        self._console.print("> understanding...")
        text = adapter.wave2text(wave_data)
        self._console.print("> you said: " + text)
        self.tick(text)

    def _speak(self, text: str) -> None:
        """
        说话.
        """
        pass

    def _markdown_print(self, text: str) -> None:
        markdown = Markdown(f"""
----

{text}
""")
        self._console.print(markdown)
