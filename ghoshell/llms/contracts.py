from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import List


class LLMTextCompletion(metaclass=ABCMeta):
    """
    最基础的 text completions
    """

    @abstractmethod
    def text_completion(self, prompt: str, config_name: str = "") -> str:
        """
        同步接口. 未来还需要实现异步接口.
        """
        pass


class LLMTextEmbedding(metaclass=ABCMeta):
    """
    生成 embedding.
    """

    @abstractmethod
    def text_embedding(self, text: str, config_name: str = "") -> List[float]:
        pass
