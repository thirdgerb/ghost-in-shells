from __future__ import annotations

import asyncio
import io
import threading
import time
import uuid
from typing import Optional, List
from wave import Wave_read

import speech_recognition as sr
import yaml
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from pyaudio import PyAudio
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown

from ghoshell.container import Provider
from ghoshell.framework.shell import ShellKernel
from ghoshell.framework.shell import ShellOutputMdw, ShellInputMdw, ShellBootstrapper
from ghoshell.ghost import Ghost
from ghoshell.messages import Input, Output, Message
from ghoshell.messages import Text, ErrMsg, Signal
from ghoshell.prototypes.playground.baidu_speech.adapter import BaiduSpeechAdapter, BaiduSpeechProvider
from ghoshell.url import URL


class BaiduSpeechShellConfig(BaseModel):
    """
    todo: 将 shell 的配置做到 configs 里.
    """
    welcome: str
    root_url: URL
    debug: bool = True


class BaiduSpeechShell(ShellKernel):
    """
    Shell
    """

    def __init__(
            self,
            ghost: Ghost,
            config_path: str,
            runtime_path: str,
            config_filename: str = "config.yml",
    ) -> None:
        self._console = Console()
        self._ghost = ghost
        self.session_id = str(uuid.uuid4().hex)
        self.user_id = str(uuid.uuid4().hex)
        self.pyaudio = PyAudio()
        super().__init__(ghost.container, config_path, runtime_path)
        self._config: BaiduSpeechShellConfig = self._load_config(config_filename)
        self._session = PromptSession("\n<<< ")
        self._shell_event: Message | None = None
        self._ghost_event: str | Message | None = None
        self._listening: bool = False
        self._time_lock: float = 0
        self._is_running: bool = True
        # thread
        self._ghost_event_thread = threading.Thread(target=self._ghost_event_loop)

    def get_providers(self) -> List[Provider]:
        return [
            BaiduSpeechProvider(),
        ]

    def get_bootstrapper(self) -> List[ShellBootstrapper]:
        return []

    def get_input_mdw(self) -> List[ShellInputMdw]:
        return []

    def get_output_mdw(self) -> List[ShellOutputMdw]:
        return []

    def _load_config(self, config_filename: str) -> BaiduSpeechShellConfig:
        config_filename = self.config_path.rstrip("/") + "/" + config_filename.lstrip("/")
        with open(config_filename) as f:
            data = yaml.safe_load(f)
        return BaiduSpeechShellConfig(**data)

    def output(self, _output: Output, _input: Input) -> None:
        signal = Signal.read(_output.payload)
        if signal is not None:
            self._on_signal(signal)
            return

        text = Text.read(_output.payload)
        if self._config.debug:
            self._console.print(_output.payload)
        if text is not None:
            self._output_text(text)

        err = ErrMsg.read(_output.payload)
        if err is not None:
            self._error_print(err)

    def _output_text(self, text: Text) -> None:
        """
        可以变更.
        """
        self._print_text(text)
        self._say(text)

    def _error_print(self, err: ErrMsg) -> None:
        self._markdown_print(f"""
# error {err.errcode} occur

{err.errmsg}

{err.stack_info}
""")

    def _print_text(self, text: Text):
        if text.markdown:
            self._markdown_print(text.content)
        else:
            self._console.print(text.content)

    def _quit(self, message: str):
        self._is_running = False
        self._ghost_event_thread.join()
        self._console.print(message)
        exit(0)

    def _on_signal(self, signal: Signal):
        if signal.code == signal.QUIT_CODE:
            self._quit("bye!")

    def parse_event(self, e: str | Message) -> Optional[Input]:
        if isinstance(e, str):
            content = e.strip()
            if content == "/exit":
                self._quit("bye!")
                return
            msg = Text(content=content)
        elif isinstance(e, Message):
            msg = e
        else:
            raise RuntimeError(f"invalid shell event {e}")

        trace = dict(
            clone_id=self.session_id,
            session_id=self.session_id,
            shell_id=self.session_id,
            shell_kind="audio_shell",
            subject_id=self.user_id,
        )
        return Input(
            mid=uuid.uuid4().hex,
            url=self._config.root_url.model_dump(),
            payload=msg.as_payload_dict(),
            trace=trace,
        )

    def run_as_app(self) -> None:
        self._welcome()
        self.handle("")
        self._ghost_event_thread.start()
        asyncio.run(self._main())

    async def _main(self):
        with patch_stdout(raw=True):
            self.dispatch("")
            await self._input_loop()
            self._console.print("Quitting event loop. Bye.")

    def dispatch(self, e: Message | str):
        self._ghost_event = e

    def _ghost_event_loop(self):
        # thread method
        while self._is_running:
            e = self._ghost_event
            if e is not None and isinstance(e, Message) or isinstance(e, str):
                self._ghost_event = None
                self.handle(e)
            time.sleep(0.2)

    async def _input_loop(self):
        while True:
            try:
                user_input = await self._session.prompt_async(multiline=False)
                self._time_lock = time.time()
                if user_input == "/exit":
                    self._quit("bye!")
                elif user_input == "":
                    self._listen()
                else:
                    self.dispatch(user_input)

            except (EOFError, KeyboardInterrupt):
                self._console.print(f"quit!!")
                exit(0)

    def handle(self, e: str | Message) -> None:
        self._console.print("> waiting ghost...")
        super().handle(e)
        self._console.print("> ghost replied")

    def _welcome(self) -> None:
        """
        todo: welcome
        """
        self._markdown_print(self._config.welcome)

    def _listen(self) -> None:
        if self._listening:
            return
        self._listening = True
        self._time_lock = time.time()
        adapter = self.container.force_fetch(BaiduSpeechAdapter)
        r = sr.Recognizer()
        with sr.Microphone() as source:
            self._console.print("> listening...")
            audio = r.listen(source)
        wave_data = audio.get_wav_data(convert_rate=16000)
        self._console.print("> speech to text...")
        text = adapter.wave2text(wave_data)
        self._console.print("> you said: " + text)
        self._listening = False

        self.dispatch(text)

    def _say(self, text: Text) -> None:
        """
        说话.
        """
        self._time_lock = time.time()
        if self._listening:
            self._console.print("> not speaking cause of listening")
            return
        adapter = self.container.force_fetch(BaiduSpeechAdapter)
        self._console.print("> text to speech...")
        speech_data = adapter.text2speech(text.content)
        self._speak(speech_data)

    def _speak(self, wave_data: bytes) -> None:
        if self._listening:
            self._console.print("> not speaking cause of listening")
            return
        self._console.print("> speaking...")
        self._speaking = True
        stream = self.pyaudio.open(
            format=self.pyaudio.get_format_from_width(2),
            channels=1,
            rate=16000,
            output=True,
        )
        wave_stream = io.BytesIO(wave_data)
        wave_obj = Wave_read(wave_stream)
        chunk = 1024
        # play stream
        speak_at = time.time()
        while self._is_running and speak_at > self._time_lock:
            frames = wave_obj.readframes(chunk)
            if not frames:
                break
            stream.write(frames)
        stream.stop_stream()
        stream.close()
        self._console.print("> finish speaking")

    def _markdown_print(self, text: str) -> None:
        markdown = Markdown(f"""
----

{text}
""")
        self._console.print(markdown)

    def deliver(self, _input: Input) -> List[Output] | None:
        return self._ghost.respond(_input)
