from ghoshell.ghost import Context
from ghoshell.llms.contracts import LLMTextCompletion


def fetch_ctx_prompter(ctx: Context) -> LLMTextCompletion:
    return ctx.container.force_fetch(LLMTextCompletion)
