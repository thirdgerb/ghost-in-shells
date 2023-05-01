from typing import Dict, Type

from langchain import OpenAI

from ghoshell.container import Provider, Container, Contract
from ghoshell.llms.contracts import LLMPrompter
from ghoshell.llms.langchain import LangChainOpenAIAdapter


class LangChainOpenAIPromptProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return LLMPrompter

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        # 暂时没有时间做复杂参数.
        return LangChainOpenAIAdapter(OpenAI(request_timeout=5))
