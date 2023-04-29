from langchain import OpenAI

from ghoshell.llms.contracts import LLMPrompt


class LangChainOpenAIAdapter(LLMPrompt):

    def __init__(self, ai: OpenAI):
        self.ai = ai
        # todo: log, records saving

    def prompt(self, prompt: str) -> str:
        return self.ai(prompt)
