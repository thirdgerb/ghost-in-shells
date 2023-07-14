from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, List, Dict

from pydantic import BaseModel

from ghoshell.ghost.context import Context
from ghoshell.ghost.mindset.operator import Operator
from ghoshell.url import URL


class Intention(BaseModel):
    """
    描述一个对外部输入信号的意图分析策略.
    意图分析策略存在许多种, 每种都会有不一样的数据结构.

    比如:
    - 自然语言
    - 消息类型
    - 事件类型
    - API
    - 命令行

    每一种预测的意图, 都应该通过不同的解析机制来解决.
    """
    kind: str
    config: Dict
    # 私有意图只有在当前任务中能被识别和匹配.
    params: Dict | None = None

    # 关联.
    target: URL | None = None
    reaction: str | None = None

    def action(self, ctx: Context) -> Operator | None:
        """
        重写这个方法可以定义全局命令.
        """
        return None


class Attention(BaseModel):
    to: URL
    intentions: List[Intention]
    reaction: str
    level: int = 0


class FocusDriver(metaclass=ABCMeta):
    """
    focus on certain kind of user intention
    fit any of attentions

    intention, attention, focus 这几个概念似乎用得并不完全匹配单词原意
    而且 intention & attention 已经成为了机器学习术语, 很容易招来术语警察.
    需要考虑将这些名词全部替换一套.
    """

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        pass

    @abstractmethod
    def register_global_intentions(self, *intentions: Intention) -> None:
        pass

    @abstractmethod
    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        pass


class Focus(metaclass=ABCMeta):
    """
    工程化的注意力机制
    在运行中接受到各种事件, 比如 api/command/设备事件等等
    通过 intentions 机制可以快速定位事件的处理者(task think => Thinking)
    """

    @abstractmethod
    def clone(self, clone_id: str) -> "Focus":
        pass

    def register(self, driver: FocusDriver) -> None:
        pass

    @abstractmethod
    def kinds(self) -> List[str]:
        pass

    @abstractmethod
    def match(self, ctx: Context, kind: str, metas: List[Intention]) -> Optional[Intention]:
        pass

    @abstractmethod
    def global_match(self, ctx: Context) -> Optional[Intention]:
        pass

    @abstractmethod
    def register_global_intentions(self, *intentions: Intention) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        提醒记得清除垃圾.
        """
        pass
