import random
import string
from typing import List
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from ghoshell.framework.stages import BasicStage
from ghoshell.ghost import *
from ghoshell.llms.utils import fetch_ctx_prompter
from ghoshell.messages import *

# todo: 优化多轮对话模板.
# 但必要性不大, 用 langchain 的方案就可以了.
RECEIVE_TEMPLATE = """
You are playing a chatbot ai "{ai_role}" to user "{user_role}"

Your instructions are: {instruction}

{ai_role}'s reply shall never be conflict to the instruction.

The conversation context are below {quote_notice}:

{dialog}

{ai_role}: 
"""


class ConversationalThinkConfig(BaseModel):
    """
    通过配置实现一个 llms 的多轮对话.
    """

    # think 的名字.
    think: str
    # think 的自我描述, 后面用于做能力的提示.
    desc: str
    # ai 扮演的角色.
    ai_role: str = "AI"
    # 用户扮演的角色.
    user_role: str = "USER"
    # 对话的最高轮次.
    max_turns: int = 25
    # 上下文允许的最大长度, 超过长度了会
    max_context_length: int = 3000
    # 对话到达了最大的轮次后, 是结束会话还是遗忘.
    conclusion_on_max_turns: bool = False
    # 默认的 debug 模式
    debug: bool = False

    # 对话内容是否需要用符号括起来, 防止 hack
    dialog_quote_mark: bool = True

    # 默认的 prompt 模板. 会用 instruction 的值去填充.
    on_receive_template: str = RECEIVE_TEMPLATE

    class Instructions(BaseModel):
        # 全局的对话说明.
        instruction: str = "你可以回复任何内容, 但请使用中文来回复."
        # 发生 prompt 事件时的回复.
        on_preempted: str = "preempting"
        # 发生 cancel 事件时的回复.
        on_canceling: str = "canceling"
        on_quiting: str = "quitting"
        on_activating: str = "activating conversational bot; talk to me"
        on_conclusion: str = ""
        on_none_text: str = "can only response text message."
        on_empty_text: str = "you speak nothing."

    instructions: Instructions = Field(default_factory=Instructions)


class Line(BaseModel):
    role: str
    text: str


class ConversationalThought(Thought):
    """
    最基本的多轮对话实现.
    """
    priority = -1

    class Vars(BaseModel):
        instruction: str = ""
        # 对话内容.
        dialog: List[Line] = Field(default_factory=lambda: [])
        # 最后一次的输入
        last_input: str = ""
        # 最后一次的回复
        last_output: str = ""
        # 是否是 debug 模式
        debug: bool = False
        # 对话的结论.
        conclusion: str = ""

    data: Vars = Vars()

    def prepare(self, args: Dict) -> None:
        if self.data is None:
            self.data = ConversationalThought.Vars()

    def set_variables(self, variables: Dict) -> None:
        self.data = ConversationalThought.Vars(**variables)

    def vars(self) -> Dict | None:
        if self.data is None:
            return None
        return self.data.model_dump()

    def _destroy(self) -> None:
        del self.data


class DefaultConversationalStage(BasicStage):

    def __init__(
            self,
            config: ConversationalThinkConfig,
            reactions: Dict[str, Reaction] = None,
            stage_name: str = "",
    ):
        self.config = config
        self.stage_name = stage_name
        self._reactions = reactions
        self._talk_start_quote = ""
        self._talk_end_quote = ""
        if config.dialog_quote_mark:
            self._talk_start_quote = "=" + "".join(random.sample(string.ascii_letters, 3)) + "="
            self._talk_end_quote = "=" + "".join(random.sample(string.ascii_letters, 3)) + "="

    def on_received(self, ctx: "Context", this: ConversationalThought, e: OnReceived) -> Operator | None:
        text = ctx.read(Text)
        # 非文字消息.
        if text is None:
            ctx.send_at(this).err(self.config.instructions.on_none_text)
            return ctx.mind(this).rewind()
        # 空消息.
        if text.is_empty():
            # todo: 也可以考虑将多个输出记录到栈里, 用 empty 来描述"继续"
            return ctx.mind(this).rewind()

        # 检查对话轮次. todo

        # 变更 this 的内容.
        self._record_dialog(ctx, this, self.config.user_role, text.content)
        #  prompt 如果发生错误, RuntimeTool.fire_event 不会保存.
        prompt = self._join_resp_prompt(this)
        if this.data.debug:
            ctx.send_at(this).text(f"# prompt(debug)\n\n{prompt}", markdown=True)

        resp = self._prompt(ctx, prompt)
        # 继续变更输出消息.
        self._record_dialog(ctx, this, self.config.ai_role, resp)

        # 删除超额的内容.
        self._check_max_turns(this)

        # 发送消息.
        ctx.send_at(this).text(resp)
        return ctx.mind(this).awaits()

    def _record_dialog(self, ctx: Context, this: ConversationalThought, role: str, content: str) -> None:
        """
        todo: 实现一个对话记录, 方便日后查阅.
        """
        this.data.last_input = content
        this.data.dialog.append(Line(role=self.config.user_role, text=content))

    def _check_max_turns(self, this: ConversationalThought) -> None:
        """
        如果超过了最大会话长度, 就删除掉历史记录.
        todo: 让 llm 自己对前文进行总结.
        """
        if len(this.data.dialog) > self.config.max_turns:
            # 删除两轮对话. 当然最好的做法应该是让 bot 自己总结.
            self._reduce_dialog(this)

    def _reduce_dialog(self, this: ConversationalThought) -> None:
        this.data.dialog = this.data.dialog[2:]

    def _prompt(self, ctx: Context, prompt: str) -> str:
        prompter = fetch_ctx_prompter(ctx)
        resp = prompter.text_completion(prompt)
        resp = resp.strip()
        if self.config.dialog_quote_mark:
            if resp.startswith(self._talk_start_quote):
                resp = resp[len(self._talk_start_quote):]
            if resp.endswith(self._talk_end_quote):
                resp = resp[:len(resp) - len(self._talk_end_quote)]
        return resp

    def _join_resp_prompt(self, this: ConversationalThought) -> str:
        dialog = []
        for line in this.data.dialog:
            info = f"{line.role}:\n{self._talk_start_quote} {line.text} {self._talk_end_quote}"
            dialog.append(info)
        quote_notice = ""
        if self.config.dialog_quote_mark:
            quote_notice = f"(each sentence is embraced with '{self._talk_start_quote}' and '{self._talk_end_quote}')"

        formatting = {
            "instruction": self.config.instructions.instruction,
            "dialog": "\n\n".join(dialog),
            "ai_role": self.config.ai_role,
            "user_role": self.config.user_role,
            "quote_notice": quote_notice,
        }
        prompt = self.config.on_receive_template.format(**formatting)
        if len(prompt) > self.config.max_context_length:
            # 执行 reduce.
            self._reduce_dialog(this)
            return self._join_resp_prompt(this)
        return prompt

    @classmethod
    def _send_and_await(cls, ctx: Context, this: ConversationalThought, content: str) -> Operator | None:
        if content:
            ctx.send_at(this).text(content)
        return ctx.mind(this).awaits()

    def on_activating(self, ctx: "Context", this: ConversationalThought, e: OnActivating) -> Operator | None:
        return self._send_and_await(ctx, this, self.config.instructions.on_activating)

    def on_quiting(self, ctx: "Context", this: ConversationalThought, e: OnQuiting) -> Operator | None:
        return self._send_and_await(ctx, this, self.config.instructions.on_quiting)

    def on_canceling(self, ctx: "Context", this: ConversationalThought, e: OnCanceling) -> Operator | None:
        return self._send_and_await(ctx, this, self.config.instructions.on_canceling)

    def on_preempt(self, ctx: "Context", this: ConversationalThought, e: OnPreempted) -> Operator | None:
        return self._send_and_await(ctx, this, self.config.instructions.on_preempted)

    def url(self) -> URL:
        return URL(think=self.config.think, stage=self.stage_name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        # todo: 下一步要实现 "能力" 的匹配.
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return self._reactions if self._reactions else {}


class ConversationalThink(Think, ThinkDriver):
    """
    先实现一个不可配置的 conversational
    用于简单测试. 
    """

    def __init__(
            self,
            # think 的名字.
            config: ConversationalThinkConfig,
            stages: List[Stage] = None,
            default_reactions: Dict[str, Reaction] = None,
    ):
        self.config = config
        if stages:
            self.stages: Dict[str, Stage] = {stage.url().stage: stage for stage in stages}
        else:
            self.stages = {}

        self.stages[""] = DefaultConversationalStage(
            self.config,
            reactions=default_reactions,
            stage_name="",
        )

    def url(self) -> URL:
        return URL(think=self.config.think)

    def driver_name(self) -> str:
        return f"{ConversationalThink.__name__}/{self.config.think}"

    def from_meta(self, meta: ThinkMeta) -> "Think":
        return self

    def to_meta(self) -> ThinkMeta:
        resolver = self.url().think
        return ThinkMeta(
            id=resolver,
            kind=f"{self.driver_name()}",
        )

    def desc(self, ctx: Context, thought: Thought) -> Any:
        # todo: 考虑让 AI 自己 description
        return self.config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        # 每次都是同一意图. 
        return self.url().new_id(extra=ctx.input.trace.model_dump(include={"session_id"}))

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        thought = ConversationalThought(args)
        # 初始化 instruction, debug 模式可以变更.
        thought.data.instruction = self.config.instructions.instruction
        # 默认的 debug 模式.
        thought.data.debug = self.config.debug
        return thought

    def result(self, ctx: "Context", this: ConversationalThought) -> Optional[Dict]:
        if this.data.conclusion:
            return {"conclusion": this.data.conclusion}
        return self._reach_conclusion(this)

    def _reach_conclusion(self, this: ConversationalThought) -> None:
        # todo
        pass

    def all_stages(self) -> List[str]:
        return list(self.stages.keys())

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        return self.stages.get(stage_name, None)
