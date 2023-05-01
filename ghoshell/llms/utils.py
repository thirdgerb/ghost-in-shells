from ghoshell.ghost import Context
from ghoshell.llms.contracts import LLMPrompter


def fetch_prompter(ctx: Context) -> LLMPrompter:
    return ctx.container.force_fetch(LLMPrompter)
