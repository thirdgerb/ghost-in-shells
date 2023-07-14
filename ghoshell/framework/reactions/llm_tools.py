from abc import ABCMeta, abstractmethod
from typing import Dict, List

from ghoshell.framework.intentions import LLMToolIntention, LLMToolIntentionResult
from ghoshell.ghost import Reaction, Context, Thought, Operator, Intention, TaskLevel


class LLMToolReaction(Reaction, metaclass=ABCMeta):
    """
    用大模型实现的工具匹配.

    需要提供每一个工具的 name: desc

    比如   {
      test: 测试
      cancel: 取消
      weather: 询问天气, 需要提供城市和日期信息.
    }

    让 LLM 来做匹配. 匹配结果会用自然语言来做参数. 比如:

    weather: 查询北京明天的天气.

    能力的描述需要足够详细, 让 llm 能够作出判断.
    """

    def __init__(self, name_2_desc: Dict, level: int = TaskLevel.LEVEL_PRIVATE):
        self._level = level
        self._name_2_desc = name_2_desc

    def level(self) -> int:
        return self._level

    def intentions(self, ctx: Context) -> List[Intention]:
        intentions = []
        for name in self._name_2_desc:
            intention = LLMToolIntention(
                config=dict(
                    name=name,
                    desc=self._name_2_desc[name],
                )
            )
            intentions.append(intention)
        return intentions

    def react(self, ctx: Context, this: Thought, params: Dict | None) -> Operator | None:
        if params is None:
            return None
        result = LLMToolIntentionResult(**params)
        return self.on_match(ctx, this, result)

    @abstractmethod
    def on_match(self, ctx: Context, this: Thought, result: LLMToolIntentionResult) -> Operator | None:
        """
        实现 on match 方法做后续的操作.
        """
        pass
