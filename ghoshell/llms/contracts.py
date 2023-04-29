from abc import ABCMeta, abstractmethod


class LLMPrompt(metaclass=ABCMeta):
    """
    最基础的 text completions
    """

    @abstractmethod
    def prompt(self, prompt: str) -> str:
        pass
