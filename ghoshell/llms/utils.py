from ghoshell.ghost import Context
from ghoshell.llms.contracts import LLMAdapter


def fetch_ctx_prompter(ctx: Context) -> LLMAdapter:
    return ctx.container.force_fetch(LLMAdapter)
