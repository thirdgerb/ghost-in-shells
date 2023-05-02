# from typing import Optional, List, Dict, Any, ClassVar
#
# import yaml
# from pydantic import BaseModel
#
# from ghoshell.ghost import *
# from ghoshell.ghost_fmk.reactions import CommandReaction
# from ghoshell.ghost_fmk.stages import AwaitStage
# from ghoshell.messages import *
#
#
# class LLMUnitTestThinkConfig(BaseModel):
#     """
#     大模型一组单元测试的基础配置.
#     """
#
#     # 测试 id
#     name: str
#     # 测试描述
#     desc: str
#     # 测试结论.
#     conclusion: str = ""
#
#     class TestCase(BaseModel):
#         # 用例介绍
#         desc: str
#         # 用例的 Prompt
#         prompt: str
#         # 期待的回复
#         expect: str
#
#     # 所有的测试用例.
#     tests: Dict[str, TestCase]
#
#
# class LLMUnitTestStorage:
#     """
#     用来读写 yaml 文件配置的简单封装.
#     """
#
#     def __init__(self, filename: str):
#         self.filename = filename
#
#     def load(self) -> LLMUnitTestThinkConfig:
#         with open(self.filename) as f:
#             config_data = yaml.safe_load(f)
#             config = LLMUnitTestThinkConfig(config_data)
#             return config
#
#     def save(self, config: LLMUnitTestThinkConfig) -> None:
#         config_data = config.dict()
#         with open(self.filename) as f:
#             yaml.safe_dump(config_data, f)
#
#
# # class LLMUnitTestThinkMeta(BaseModel):
# #     think_name: str
# #
# #     def to_think_meta(self) -> ThinkMeta:
# #         return ThinkMeta(
# #             id=self.think_name,
# #             driver=LLMUnitTestThink.driver_name(),
# #             config=dict(),
# #         )
#
#
# class LLMUnitTestThink(Think, ThinkDriver, Stage):
#     """
#     实现一个极简的单元测试用例, 方便自己重复测试各种 prompt.
#     更好的实现是记录到本地缓存, 并且直接生成 Think. 先不着急实现这个 feature, 很容易.
#     """
#
#     # 单测所在文件的目录, 需要在 bootstrap 环节完成定义.
#     root_path: ClassVar[str] = ""
#
#     def __init__(self, think_name: str):
#         self.think_name = think_name
#         filename = self.root_path.rstrip("/") + "/" + think_name.lstrip("/") + ".yaml"
#         self.storage = LLMUnitTestStorage(filename)
#         self.config = self.storage.load()
#
#     def url(self) -> URL:
#         return URL(resolver=self.think_name)
#
#     def to_meta(self) -> ThinkMeta:
#         return ThinkMeta(
#             id=self.config.name,
#             kind=self.driver_name(),
#             config=dict(),
#         )
#
#     @classmethod
#     def driver_name(cls) -> str:
#         return cls.__name__
#
#     def from_meta(self, meta: ThinkMeta) -> "Think":
#         """
#         简单测试一下, 完全基于 Meta 配置来生成.
#         """
#         return LLMUnitTestThink(meta.id)
#
#     def description(self, thought: Thought) -> Any:
#         """
#         当 Think 作为能力提供的时候, 需要实现 description
#         """
#         return self.config.desc
#
#     def new_task_id(self, ctx: "Context", args: Dict) -> str:
#         return self.url().new_id()
#
#     def new_thought(self, ctx: "Context", args: Dict) -> Thought:
#         """
#         完全为了测试, 等需要上下文再开发.
#         """
#         return DictThought(args)
#
#     def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
#         return None
#
#     def all_stages(self) -> List[str]:
#         return list(self.config.tests.keys())
#
#     def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
#         if stage_name == "":
#             return self
#         if stage_name in self.config.tests:
#             config = self.config.tests[stage_name]
#             return LLMUnitTestCaseStage(self.config.name, config, self.storage)
#         return None
#
#     def intentions(self, ctx: Context) -> List[Intention] | None:
#         return None
#
#     def reactions(self) -> Dict[str, Reaction]:
#         return {}
#
#     def on_event(self, ctx: "Context", this: DictThought, event: Event) -> Operator | None:
#         if isinstance(event, OnActivating):
#             return self.on_activating(ctx, this)
#         if isinstance(event, OnReceived):
#             return self.on_receiving(ctx, this)
#         ctx.send_at(this).text(f"receive unhandled event {event}")
#         return None
#
#     activating_template: ClassVar[str] = """
# # LLMs UnitTest {name}
#
# desc: {desc}
#
# cases:
# {cases}
#
# instruction:
#
# - input [case name] shall run single test case
# - input "/help" see what commands can be useful
# """
#
#     def on_activating(self, ctx: Context, this: DictThought) -> Operator | None:
#         cases = []
#         # activated = this.data.get("activated", False)
#         # if not activated:
#         for case in self.config.tests:
#             line = f"- {case.name}: {case.desc}"
#             cases.append(line)
#         _format = {
#             "name": self.config.name,
#             "desc": self.config.desc,
#             "cases": "\n".join(cases)
#         }
#         _output = self.activating_template.format(**_format)
#         ctx.send_at(this).text(_output, markdown=True)
#         # this.data["activated"] = True
#         return ctx.mind(this).awaits()
#
#     def on_receiving(self, ctx: Context, this: DictThought) -> Operator | None:
#         text = ctx.read(Text)
#         this.vars()
#         if text is None:
#             ctx.send_at(this).err("can only receive text message")
#             return ctx.mind(this).rewind()
#         if text.is_empty():
#             return ctx.mind(this).rewind()
#
#         content = text.content.strip()
#         tests = {case.name: case for case in self.config.tests}
#         if content == "cancel":
#             return ctx.mind(this).cancel()
#
#         if content in tests:
#             return ctx.mind(this).forward(content)
#
#         ctx.send_at(this).err(f"you said: {content} \n\ncan not handle")
#         return ctx.mind(this).repeat()
#
#
# class RunTestCaseStage(AwaitStage):
#     """
#     运行单元测试, 查看结果.
#     """
#
#     def url(self) -> URL:
#         pass
#
#     def intentions(self, ctx: Context) -> List[Intention] | None:
#         return None
#
#     def reactions(self) -> Dict[str, Reaction]:
#         return {
#             # 允许编辑, 进入编辑模式.
#             "/edit": EditTestCaseCmdReaction(),
#             # 允许复制一个新的.
#             "/copy": CopyTestCaseCmdReaction(),
#         }
#
#     def on_received(self, ctx: "Context", this: Thought, e: OnReceived) -> Operator | None:
#         pass
#
#     def on_activating(self, ctx: "Context", this: Thought, e: Event) -> Operator | None:
#         pass
#
#     def on_quiting(self, ctx: "Context", this: Thought, e: OnQuiting) -> Operator | None:
#         pass
#
#     def on_canceling(self, ctx: "Context", this: Thought, e: OnCanceling) -> Operator | None:
#         pass
#
#     def on_preempt(self, ctx: "Context", this: Thought, e: OnPreempted) -> Operator | None:
#         pass
#
#
# class EditTestCaseStage(Stage):
#     """
#     编辑一个单元测试用例.
#     """
#     pass
#
#
# class ConversationalTestStage(Stage):
#     """
#     多轮对话单元测试. 这是假设当前的单元测试是一个多轮对话.
#     """
#     pass
#
#
# # ---- reactions ---- #
#
#
# class RunTestCaseCmdReaction(CommandReaction):
#     """
#     命令: 运行一个单元测试, 查看结果.
#     """
#     pass
#
#
# class SaveTestCaseCmdReaction(CommandReaction):
#     """
#     命令: 保存当前对话中的 prompt, 作为单元测试的用例.
#     """
#     pass
#
#
# class EditTestCaseCmdReaction(CommandReaction):
#     """
#     命令: 把当前单元测试进入编辑模式.
#     """
#     pass
#
#
# class NewTestCaseCmdReaction(CommandReaction):
#     """
#     命令: 创建一个新的单元测试, 并进入编辑模式.
#     如果测试用例已经存在, 会报失败.
#     """
#     pass
#
#
# class CopyTestCaseCmdReaction(CommandReaction):
#     """
#     命令: 复制当前的单元测试, 成为一个新的单测.
#     进入目标单元测试的编辑模式.
#     """
#     pass
#
# # class LLMUnitTestCaseStage(Stage):
# #
# #     def __init__(
# #             self,
# #             think_name: str,
# #             stage_name: str,
# #             case: LLMUnitTestThinkConfig.TestCase,
# #             storage: LLMUnitTestStorage,
# #     ):
# #         self.think_name = think_name
# #         self.stage_name = stage_name
# #         self.config = case
# #         self.storage = storage
# #
# #     def url(self) -> URL:
# #         return URL(resolver=self.think_name, stage=self.config.name)
# #
# #     def intentions(self, ctx: Context) -> List[Intention] | None:
# #         return None
# #
# #     def reactions(self) -> Dict[str, Reaction]:
# #         return {}
# #
# #     def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
# #         if isinstance(event, OnActivating):
# #             return self.describe_test_case(ctx, this)
# #         elif isinstance(event, OnReceived):
# #             return self.run_test_case(ctx, this)
# #         else:
# #             return None
# #
# #     def describe_test_case(self, ctx: "Context", this: Thought) -> Operator:
# #         prompt = self.config.prompt
# #         ctx.send_at(this).markdown(f"""
# # ## run case {self.config.name}
# #
# # description: {self.config.desc}
# #
# # prompt:
# # ```
# # {prompt}
# # ```
# # """)
# #         ctx.send_at(this).text("input any to run test")
# #         return ctx.mind(this).awaits()
# #
# #     def run_test_case(self, ctx: Context, this: DictThought) -> Operator:
# #         waiting = this.data.get("waiting", False)
# #         if not waiting:
# #             prompter = fetch_prompter(ctx)
# #             resp = prompter.prompt(self.config.prompt)
# #             ctx.send_at(this).markdown(f"""
# #     ## response
# #
# #     {resp}
# #
# #     ## expect
# #     {self.config.expect}
# #     """)
# #             this.data["waiting"] = True
# #             ctx.send_at(this).markdown("input anything to return")
# #             return ctx.mind(this).awaits()
# #         else:
# #             this.data["waiting"] = False
# #             return ctx.mind(this).restart()
