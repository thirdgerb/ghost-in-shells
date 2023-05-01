from abc import ABCMeta, abstractmethod


class LLMPrompter(metaclass=ABCMeta):
    """
    最基础的 text completions
    """

    @abstractmethod
    def prompt(self, prompt: str) -> str:
        pass
