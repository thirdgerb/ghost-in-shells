from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from ghoshell.ghost import *
from ghoshell.ghost_fmk.stages import AwaitStage


class LLMUnitTestThinkConfig(BaseModel):
    think_name: str
    desc: str = ""


class LLMUnitTestThink(Think, ThinkDriver):
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
        pass

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        pass


class LLMUnitTestStage(AwaitStage):

    def on_received(self, ctx: "Context", this: Thought, e: OnReceived) -> Operator | None:
        pass

    def on_activating(self, ctx: "Context", this: Thought, e: OnActivating) -> Operator | None:
        pass

    def on_quiting(self, ctx: "Context", this: Thought, e: OnQuiting) -> Operator | None:
        pass

    def on_canceling(self, ctx: "Context", this: Thought, e: OnCanceling) -> Operator | None:
        pass

    def on_preempt(self, ctx: "Context", this: Thought, e: OnPreempted) -> Operator | None:
        pass
