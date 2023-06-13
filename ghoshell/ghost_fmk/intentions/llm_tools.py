from typing import List, Optional, Dict

from pydantic import BaseModel

from ghoshell.ghost import Intention, Context, FocusDriver, CtxTool
from ghoshell.llms import LLMPrompter
from ghoshell.messages import Text


class LLMToolIntention(Intention):
    """
    给 大模型用的工具提示
    """
    kind = "llm_tools"

    class Result(BaseModel):
        # 调用工具时提供的上下文.
        context: str

    # name: desc
    config: Dict

    params: Result | None = None


class LLMToolAgentConfig(BaseModel):
    instruction = """
我是一个自然语言理解中间件 (NLU), 在思考用户说得话是否正好对应我的某种工具.
这些工具也是基于大语言模型实现的. 

以下是对我的思考有帮助的各种工具 (格式是 `name`: `desc`) :

{tools}

当前的上下文如下: 

{context}

如果用户的消息匹配某一个工具, 我需要用 `name: context` 的格式返回对这个工具的调用方法. 
这里 name 是工具的名称, 而 context 则是我调用工具时, 给工具传入的上下文. 
如果没有正好匹配某个工具, 我应该返回 `{invalid}`, 表示不使用任何工具. 

用户的消息如下: 

{message}

我的思考如下: 
"""

    tool_temp = "* {name}: {desc}"

    invalid_mark = "no"


class LLMToolAgentDriver(FocusDriver):

    def __init__(self, config: LLMToolAgentConfig, prompter: LLMPrompter):
        self.global_tools: List[LLMToolIntention] = []
        self.prompter = prompter
        self.config = config

    def kind(self) -> str:
        return LLMToolIntention.kind

    def match(self, ctx: Context, *metas: LLMToolIntention) -> Optional[LLMToolIntention]:
        text = Text.read(ctx.input.payload)
        if text is None:
            return None
        if text.is_empty():
            return None
        return self._match_content(ctx, text.content, *metas)

    def _match_content(self, ctx: Context, content: str, *metas: LLMToolIntention) -> Optional[LLMToolIntention]:
        tool_list = []
        tool_map = {}
        tools = []
        for meta in metas:
            for name in meta.config:
                if name in tool_map:
                    # 不重复
                    continue
                tool_list.append(name)
                tool_map[name] = meta
                tool_desc = self.config.tool_temp.format(name=name, desc=meta.config[name])
                # 添加所有的 tools
                tools.append(tool_desc)

        tools_str = "\n".join(tools)
        stage = CtxTool.current_think_stage(ctx)
        context_str = stage.desc()
        prompt = self.config.instruction.format(
            context=context_str,
            tools=tools_str,
            message=content,
            invalid=self.config.invalid_mark,
        )

        prompter = ctx.container.force_fetch(LLMPrompter)
        resp = prompter.prompt(prompt)
        # 没有任何匹配.
        if resp == self.config.invalid_mark:
            return None

        index = resp.strip().find(':')
        if index > 0:
            name = resp[:index].strip()
            desc = resp[index + 1:].strip()
        else:
            name = resp
            desc = ""

        if name not in tool_map:
            return None

        matched = tool_map[name]
        matched.params = LLMToolIntention.Result(context=desc)
        return matched

    def register_global_intentions(self, *intentions: Intention) -> None:
        for i in intentions:
            wrapped = LLMToolIntention(**i.dict())
            self.global_tools.append(wrapped)

    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        if len(self.global_tools) > 0:
            return self.match(ctx, *self.global_tools)
        return None
