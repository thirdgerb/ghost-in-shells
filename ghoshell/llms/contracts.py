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

#
# class Prompter(metaclass=ABCMeta):
#     """
#     对 chat completion 或 text completion 的封装.
#     """
#
#     @abstractmethod
#     def prompt(self, prompt: str, prompter_id: str = "") -> str:
#         pass
#
#
# class PromptTemp(BaseModel, metaclass=ABCMeta):
#     prompter: ClassVar[str]
#
#     @abstractmethod
#     def as_prompt(self) -> str:
#         pass
#
#     def __call__(self, container: Container) -> str:
#         prompter = container.force_fetch(Prompter)
#         return prompter.prompt(self.as_prompt(), self.prompter)
