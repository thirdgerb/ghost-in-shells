import time
from logging import Logger
from typing import Dict

from langchain import OpenAI

from ghoshell.llms.contracts import LLMAdapter


class LangChainOpenAIAdapter(LLMAdapter):

    def __init__(self, ai: OpenAI, logger: Logger):
        self.ai = ai
        self.logger = logger
        self.adapters: Dict[str, LLMAdapter] = {}

    def name(self) -> str:
        return "langchain"

    def register_adapter(self, adapter: LLMAdapter) -> None:
        self.adapters[adapter.name()] = adapter

    def get_adapter(self, adapter_name: str = "") -> LLMAdapter | None:
        if adapter_name == self.name():
            return self
        for adapter in self.adapters.values():
            got = adapter.get_adapter(adapter_name)
            if got is not None:
                return got
        return None

    def text_completion(self, prompt: str) -> str:
        self.logger.debug(f"prompt: >>> {prompt}")
        resp = self.ai(prompt)
        self.logger.debug(f"prompt resp: >>> {resp}")
        # 避免高并发
        time.sleep(0.1)
        return resp
