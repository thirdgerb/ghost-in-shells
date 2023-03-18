from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Dict, Tuple

from pydantic import BaseModel

from ghoshell.ghost.context import IContext
from ghoshell.ghost.uml import UML

if TYPE_CHECKING:
    from context import Context

    INTENTION_KIND = TypeVar('INTENTION_KIND', bound=str)
    INTENTION_LEVEL = TypeVar('INTENTION_LEVEL', bound=int)


class IntentionMeta(BaseModel):
    kind: str
    params: Dict = {}


class Intention(metaclass=ABCMeta):
    """
    对上下文进行意图解析.
    比如:
    - 自然语言
    - 消息类型
    - 事件类型
    - API
    - 命令行

    解析的结果应该包含参数.
    """

    @property
    @abstractmethod
    def uml(self) -> UML:
        """
        如果 intention 命中了, 会路由到一个 uml 中.
        """
        pass

    @abstractmethod
    def match(self, ctx: IContext) -> Tuple[bool, Dict]:
        """
        是否匹配上下文.
        返回值 Tuple 第一个是匹配的结果. 第二个是解析出来的参数. 这个参数不要为 None 了.
        Intention 实际运行时可以有很多种组合, 但每种组合都需要返回相同的参数结构, 是一种协议.
        """
        pass

    @abstractmethod
    def metas(self) -> Dict[str, IntentionMeta]:
        """
        intention 返回 metas, 可以放入 output 中, 方便做分析.
        举个例子, intention 中包含 choice 类型
        则多个 Intention 可以组装合并到一个 Choose 问题中.
        又比如说 intention 可以使用 Command 命令模式, 则用户调用 /help 时, 应该返回所有的命令介绍.
        """
        pass


class Attentions(metaclass=ABCMeta):
    """
    工程化的注意力机制
    在运行中接受到各种事件, 比如 api/command/设备事件等等
    通过 attentions 机制可以快速定位事件的处理者(reaction)
    """

    def match(self, ctx: Context) -> bool:
        pass
