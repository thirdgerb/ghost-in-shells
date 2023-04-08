from abc import ABCMeta, abstractmethod
from typing import List

from pydantic import BaseModel

from ghoshell.ghost.io import Input, Output, Trace


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

    @abstractmethod
    def save_input(self, _input: Input) -> None:
        pass

    @abstractmethod
    def save_output(self, _output: Output) -> None:
        pass
