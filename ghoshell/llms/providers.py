import os
from logging import Logger
from typing import Dict, Type

from langchain import OpenAI

from ghoshell.container import Provider, Container, Contract
from ghoshell.llms.adapters import LangChainOpenAIAdapter
from ghoshell.llms.contracts import LLMAdapter


class LangChainOpenAIPromptProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return LLMAdapter

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        # todo: 回头根据命名可以进行不同的设置.
        proxy = os.environ.get("OPENAI_PROXY", None)
        ai = OpenAI(
            request_timeout=30,
            max_tokens=512,
            model_name="text-davinci-003",
            max_retries=0,
            openai_proxy=proxy,
        )
        logger = con.force_fetch(Logger)
        # 暂时没有时间做复杂参数.
        return LangChainOpenAIAdapter(ai, logger)
