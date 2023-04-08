from abc import ABCMeta, abstractmethod
from typing import List, Optional, Dict

from pydantic import BaseModel

from ghoshell.ghost.io import Input, Output, Trace, Payload


class Searcher(BaseModel):
    trace: Trace = None
    message_id__in: List[str] = []
    task_id__in: List[str] = []
    offset_message_id: str = ""
    limit: int = 30


class Session(metaclass=ABCMeta):

    @property
    @abstractmethod
    def session_id(self) -> str:
        pass

    @property
    @abstractmethod
    def env(self) -> Dict:
        """
        根据协议定义的环境信息.
        """
        pass

    @abstractmethod
    def save_input(self, _input: Input) -> None:
        pass

    @abstractmethod
    def save_output(self, _output: Output) -> None:
        pass

    @abstractmethod
    def search_messages(self, searcher: Searcher) -> List[Payload]:
        pass

    @abstractmethod
    def fetch_message(self, msg_id: str) -> Optional[Payload]:
        pass
