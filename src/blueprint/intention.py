from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, TypeVar, Dict

if TYPE_CHECKING:
    from context import Context

    INTENTION_CATEGORY = TypeVar('INTENTION_CATEGORY', bound=str)
    INTENTION_LEVEL = TypeVar('INTENTION_LEVEL', bound=int)


class Intention(metaclass=ABCMeta):
    """
    对某种意图的结构化描述
    意图可能会有各种分类
    """
    category: INTENTION_CATEGORY
    level: INTENTION_LEVEL
    priority: float
    args: Dict


class Attentions(metaclass=ABCMeta):
    """
    工程化的注意力机制
    在运行中接受到各种事件, 比如 api/command/设备事件等等
    通过 attentions 机制可以快速定位事件的处理者(reaction)
    """

    def match(self, ctx: Context, category: INTENTION_CATEGORY, arguments: Dict) -> bool:
        pass
