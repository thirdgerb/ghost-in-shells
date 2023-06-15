from __future__ import annotations

from abc import ABCMeta, abstractmethod


class LLMAdapter(metaclass=ABCMeta):
    """
    最基础的 text completions
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def register_adapter(self, adapter: LLMAdapter) -> None:
        pass

    @abstractmethod
    def get_adapter(self, adapter_name: str = "") -> LLMAdapter | None:
        pass

    @abstractmethod
    def text_completion(self, prompt: str) -> str:
        pass
