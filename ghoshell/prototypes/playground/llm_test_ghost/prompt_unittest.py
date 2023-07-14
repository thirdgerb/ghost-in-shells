import os
from typing import Dict, ClassVar, List, Optional, Any, Iterator

from pydantic import BaseModel, Field

from ghoshell.ghost import *
from ghoshell.llms.utils import fetch_ctx_prompter
from ghoshell.messages import *


class PromptUnitTestConfig(BaseModel):
    DESC_MARK: ClassVar[str] = "# DESC"
    PROMPT_MARK: ClassVar[str] = "# PROMPT"
    EXPECT_MARK: ClassVar[str] = "# EXPECT"
    CONCLUSION_MARK: ClassVar[str] = "# CONCLUSION"

    """
    对 Prompt 进行单元测试的用例.
    需要指向某个文件夹, 读取文件来作为测试用例.

    举例:
    unittest/
        test_name/
            index.md   # 索引文件, 用来描述测试用例的思路.
            teat_case_filename1.md  # 测试用例 1, stage name == test_case_filename1   (文件名就是状态名)
            teat_case_filename2.md  # 测试用例 2
            teat_case_filename3.md  # 测试用例 3
    """
    # 测试描述
    index: str = ""

    class TestCase(BaseModel):
        """
        用 Markdown 的方式来记录测试用例.
        用一级标题来分割不同的属性.

        # desc\n
        描述用例的说明
        # prompt\n
        描述用例的 prompt
        # expect\n
        描述用例的期待结果.
        """
        # 用例介绍
        desc: str = ""
        # 用例的 Prompt
        prompt: str = ""
        # 期待的回复
        expect: str = ""
        # conclusion 测试的结论.
        conclusion: str = ""

    # 所有的测试用例.
    tests: Dict[str, TestCase] = Field(default_factory=dict)


class PromptUnitTestLoader:

    def __init__(
            self,
            dirname: str,
            index_name: str,
            md_suffix: str,
    ):
        self.dirname = dirname
        self.index_name = index_name
        self.md_suffix = md_suffix
        self.index_content = ""
        self.stage_configs: Dict[str, PromptUnitTestConfig.TestCase] = {}

    def load(self) -> PromptUnitTestConfig:
        index_filename = self.index_name + self.md_suffix
        for root, ds, fs in os.walk(self.dirname):
            for filename in fs:
                fullname = self.dirname + "/" + filename
                if not filename.endswith(self.md_suffix):
                    continue
                with open(fullname) as f:
                    content = f.read()
                    if filename == index_filename:
                        self.index_content = content.strip()
                    else:
                        stage_name = filename[:len(filename) - len(self.md_suffix)]
                        test_case = self.load_test_case(content)
                        self.stage_configs[stage_name] = test_case
        return self._integration()

    @classmethod
    def load_test_case(cls, joint: str) -> PromptUnitTestConfig.TestCase:
        lines = joint.split("\n")
        mark_idxes = {
            "desc": -1,
            "prompt": -1,
            "expect": -1,
            "conclusion": -1,
        }
        start_end_dict: Dict[int, int] = {}
        mark_idx = -1
        idx = 0
        for line in lines:
            is_mark = False
            match line.strip():
                case PromptUnitTestConfig.DESC_MARK:
                    mark_idxes["desc"] = idx
                    is_mark = True
                case PromptUnitTestConfig.PROMPT_MARK:
                    mark_idxes["prompt"] = idx
                    is_mark = True
                case PromptUnitTestConfig.EXPECT_MARK:
                    mark_idxes["expect"] = idx
                    is_mark = True
                case PromptUnitTestConfig.CONCLUSION_MARK:
                    mark_idxes["conclusion"] = idx
                    is_mark = True

            if is_mark:
                if mark_idx >= 0:
                    start_end_dict[mark_idx] = idx
                mark_idx = idx
            idx += 1
        # 继续记录.
        if mark_idx >= 0:
            start_end_dict[mark_idx] = idx

        config = PromptUnitTestConfig.TestCase()
        for key in ["desc", "prompt", "expect", "conclusion"]:
            mark_at = mark_idxes[key]
            if mark_at >= 0:
                end = start_end_dict.get(mark_at)
                start = mark_at + 1
                selected = lines[start:end]
                joint = "\n".join(selected).strip()
                setattr(config, key, joint.strip())
        return config

    def _integration(self) -> PromptUnitTestConfig:
        config = PromptUnitTestConfig()
        config.index = self.index_content
        config.tests = self.stage_configs
        return config


class PromptUnitTestThinkDriver(ThinkDriver):

    def __init__(
            self,
            # 所有测试用例所在的本地目录. 用文件来做比较简单.
            root_dir: str,
            # 默认用 md 作为数据.
            md_suffix: str = ".md",
            # 索引文件的名称.
            index_name: str = "index",
            think_prefix: str = "prefix"
    ):
        self.md_suffix = md_suffix
        self.index_name = index_name
        self.think_prefix = think_prefix
        self.root_dir = root_dir

    @classmethod
    def driver_name(cls) -> str:
        return cls.__name__

    def foreach_think(self) -> Iterator[ThinkMeta]:
        for root, ds, fs in os.walk(self.root_dir):
            for dirname in ds:
                think_name = self.think_prefix.rstrip("/") + "/" + dirname
                yield ThinkMeta(
                    id=think_name,
                    kind=self.driver_name(),
                )

    def from_meta(self, meta: ThinkMeta) -> "Think":
        think_name = meta.id
        if not think_name.startswith(self.think_prefix):
            raise MindsetNotFoundException(f"think {think_name} not found in prompt unittest thinks")
        sub_dir = think_name[len(self.think_prefix):]
        dirname = self.root_dir.rstrip("/") + "/" + sub_dir
        storage = PromptUnitTestLoader(
            dirname,
            self.index_name,
            self.md_suffix,
        )
        return PromptUnitTestThink(meta.id, storage)


class PromptUnitTestThink(Think, Stage):
    """
    用于测试 Prompt 的单元测试.
    """

    def __init__(
            self,
            think_name: str,
            loader: PromptUnitTestLoader,
    ):
        self.think_name = think_name
        self.loader = loader
        self.config = loader.load()

    def url(self) -> URL:
        return URL.new_think(self.think_name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self.think_name,
            kind=PromptUnitTestThinkDriver.driver_name(),
        )

    def desc(self, ctx: Context, thought: Thought) -> Any:
        return self.config.index

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        # 全局唯一.
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return DictThought(args)

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        # todo: 暂时没有依赖方.
        return None

    def all_stages(self) -> List[str]:
        stages = list(sorted(self.config.tests.keys()))
        stages.append("")
        # 偷懒, 写个低效率的实现.
        return list(set(stages))

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if stage_name == "":
            return self
        if stage_name not in self.config.tests:
            return None
        case = self.config.tests[stage_name]
        return PromptUnitTestCaseStage(self.think_name, stage_name, case)

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

## desc

{desc}

## cases:

{cases}

## instruction:

- input "/all" shall run all the tests in orders
- input [case name] shall run single test case
- input "/reload" will reload stages from files
- input "/help" see what commands can be useful.
"""

    def on_activating(self, ctx: Context, this: DictThought) -> Operator | None:
        cases = []
        names = self.config.tests.keys()
        names = sorted(names)
        for name in names:
            case = self.config.tests[name]
            line = f"- {name}: {case.desc}"
            cases.append(line)

        formation = {
            "name": self.think_name,
            "desc": self.config.index,
            "cases": "\n".join(cases)
        }
        _output = self.activating_template.format(**formation)
        ctx.send_at(this).text(_output, markdown=True)
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
        if content == "cancel":
            return ctx.mind(this).cancel()

        if content == "/all":
            keys = list(self.config.tests.keys())
            ctx.send_at(this).text(f"forward test cases: {keys}")
            return ctx.mind(this).forward(*keys)

        if content == "/reload":
            self.config = self.loader.load()
            ctx.send_at(this).text(f"reload test files")
            return ctx.mind(this).restart()

        if content in self.config.tests:
            return ctx.mind(this).forward(content, "")

        ctx.send_at(this).err(f"you said: {content} \n\ncan not handle")
        return ctx.mind(this).repeat()


class PromptUnitTestCaseStage(Stage):
    """
    一个单元测试用例.
    """

    def __init__(self, think_name: str, stage_name: str, case: PromptUnitTestConfig.TestCase):
        self.think_name = think_name
        self.stage_name = stage_name
        self.config = case

    def url(self) -> URL:
        return URL(think=self.think_name, stage=self.stage_name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {}

    def on_event(self, ctx: "Context", this: DictThought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.describe_test_case(ctx, this)
        elif isinstance(event, OnReceived):
            return self.run_test_case(ctx, this)
        else:
            return None

    def describe_test_case(self, ctx: "Context", this: Thought) -> Operator:
        prompt = self.config.prompt
        ctx.send_at(this).markdown(f"""
# run case {self.think_name + "::" + self.stage_name}

## description 

{self.config.desc}

## prompt
```
{prompt}
```

## expect

{self.config.expect}

## conclusion

{self.config.conclusion}
""")
        ctx.send_at(this).text("input any to run test")
        return ctx.mind(this).awaits()

    def run_test_case(self, ctx: Context, this: DictThought) -> Operator:
        committed = this.data.get("committed", False)
        if committed:
            this.data["committed"] = False
            return ctx.mind(this).forward()
        else:
            prompter = fetch_ctx_prompter(ctx)
            resp = prompter.text_completion(self.config.prompt)

            ctx.send_at(this).markdown(resp).markdown("press anything to continue")
            this.data["committed"] = True
            return ctx.mind(this).awaits()
