import os
from logging import Logger
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
        # todo: 回头根据命名可以进行不同的设置.
        proxy = os.environ.get("OPENAI_PROXY", None)
        ai = OpenAI(
            request_timeout=30,
            max_tokens=2048,
            model_name="text-davinci-003",
            max_retries=0,
            openai_proxy=proxy,
        )
        logger = con.force_fetch(Logger)
        # 暂时没有时间做复杂参数.
        return LangChainOpenAIAdapter(ai, logger)
