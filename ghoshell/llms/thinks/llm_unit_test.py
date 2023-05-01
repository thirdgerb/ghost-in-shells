from typing import Optional, List, Dict, Any, ClassVar

from pydantic import BaseModel

from ghoshell.ghost import *
from ghoshell.llms.utils import fetch_prompter
from ghoshell.messages import *


class LLMUnitTestThinkConfig(BaseModel):
    # 测试 id
    think_name: str
    desc: str
    # 测试结论.
    conclusion: str = ""

    class TestCase(BaseModel):
        # 用例名
        name: str
        desc: str
        # 用例的上下文
        prompt: str
        # 期待的回复
        expect: str

    tests: List[TestCase]


class LLMUnitTestThink(Think, ThinkDriver, Stage):
    """
    实现一个极简的单元测试用例, 方便自己重复测试各种 prompt.
    更好的实现是记录到本地缓存, 并且直接生成 Think. 先不着急实现这个 feature, 很容易.
    """

    def __init__(self, config: LLMUnitTestThinkConfig):
        self._config = config

    def url(self) -> URL:
        return URL(resolver=self._config.think_name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self._config.think_name,
            kind=self.driver_name(),
            config=self._config.dict(),
        )

    def driver_name(self) -> str:
        return self.__class__.__name__

    def from_meta(self, meta: ThinkMeta) -> "Think":
        """
        简单测试一下, 完全基于 Meta 配置来生成.
        """
        config = LLMUnitTestThinkConfig(**meta.config)
        return LLMUnitTestThink(config)

    def description(self, thought: Thought) -> Any:
        """
        当 Think 作为能力提供的时候, 需要实现 description
        """
        return self._config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        """
        完全为了测试, 等需要上下文再开发.
        """
        return DictThought(args)

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        return None

    def all_stages(self) -> List[str]:
        names = set("")
        for case in self._config.tests:
            names.add(case.name)
        return list(names)

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if stage_name == "":
            return self
        tests = {case.name: case for case in self._config.tests}
        if stage_name in tests:
            config = tests[stage_name]
            return LLMUnitTestCaseStage(self._config.think_name, config)
        return None

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {}

    def on_event(self, ctx: "Context", this: DictThought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activating(ctx, this)
        if isinstance(event, OnReceived):
            return self.on_receiving(ctx, this)
        ctx.send_at(this).text(f"receive unhandled event {event}")
        return None

    activating_template: ClassVar[str] = """
# LLMs UnitTest {name}

desc: {desc}

cases:
{cases}

instruction:

- input [case name] shall run single test case
- input "/help" see what commands can be useful
"""

    def on_activating(self, ctx: Context, this: DictThought) -> Operator | None:
        cases = []
        # activated = this.data.get("activated", False)
        # if not activated:
        for case in self._config.tests:
            line = f"- {case.name}: {case.desc}"
            cases.append(line)
        _format = {
            "name": self._config.think_name,
            "desc": self._config.desc,
            "cases": "\n".join(cases)
        }
        _output = self.activating_template.format(**_format)
        ctx.send_at(this).text(_output, markdown=True)
        # this.data["activated"] = True
        return ctx.mind(this).awaits()

    def on_receiving(self, ctx: Context, this: DictThought) -> Operator | None:
        text = ctx.read(Text)
        this.vars()
        if text is None:
            ctx.send_at(this).err("can only receive text message")
            return ctx.mind(this).rewind()
        if text.is_empty():
            return ctx.mind(this).rewind()

        content = text.content.strip()
        tests = {case.name: case for case in self._config.tests}
        if content == "cancel":
            return ctx.mind(this).cancel()

        if content in tests:
            return ctx.mind(this).forward(content)

        ctx.send_at(this).err(f"you said: {content} \n\ncan not handle")
        return ctx.mind(this).repeat()


class LLMUnitTestCaseStage(Stage):

    def __init__(self, think: str, case: LLMUnitTestThinkConfig.TestCase):
        self.think = think
        self.config = case

    def url(self) -> URL:
        return URL(resolver=self.think, stage=self.config.name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {}

    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.describe_test_case(ctx, this)
        elif isinstance(event, OnReceived):
            return self.run_test_case(ctx, this)
        else:
            return None

    def describe_test_case(self, ctx: "Context", this: Thought) -> Operator:
        prompt = self.config.prompt
        ctx.send_at(this).markdown(f"""
## run case {self.config.name}

description: {self.config.desc}

prompt:
```
{prompt}
```
""")
        ctx.send_at(this).text("input any to run test")
        return ctx.mind(this).awaits()

    def run_test_case(self, ctx: Context, this: DictThought) -> Operator:
        waiting = this.data.get("waiting", False)
        if not waiting:
            prompter = fetch_prompter(ctx)
            resp = prompter.prompt(self.config.prompt)
            ctx.send_at(this).markdown(f"""
    ## response

    {resp}

    ## expect
    {self.config.expect}
    """)
            this.data["waiting"] = True
            ctx.send_at(this).markdown("input anything to return")
            return ctx.mind(this).awaits()
        else:
            this.data["waiting"] = False
            return ctx.mind(this).restart()
