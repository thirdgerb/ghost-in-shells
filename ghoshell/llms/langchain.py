import time
from logging import Logger

from langchain import OpenAI

from ghoshell.llms.contracts import LLMPrompter


class LangChainOpenAIAdapter(LLMPrompter):

    def __init__(self, ai: OpenAI, logger: Logger):
        self.ai = ai
        self.logger = logger

    def prompt(self, prompt: str) -> str:
        self.logger.debug(f"prompt: >>> {prompt}")
        resp = self.ai(prompt)
        self.logger.debug(f"prompt resp: >>> {resp}")
        # 避免高并发
        time.sleep(0.1)
        return resp
