import time
from logging import Logger

from langchain import OpenAI

from ghoshell.llms.contracts import LLMPrompter


class LangChainOpenAIAdapter(LLMPrompter):

    def __init__(self, ai: OpenAI, logger: Logger):
        self.ai = ai
        self.logger = logger

    def prompt(self, prompt: str) -> str:
        resp = self.ai(prompt)
        # 避免高并发
        time.sleep(0.1)
        return resp.strip()
