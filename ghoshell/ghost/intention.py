from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, TypeVar, Dict

if TYPE_CHECKING:
    from context import Context

    INTENTION_KIND = TypeVar('INTENTION_KIND', bound=str)
    INTENTION_LEVEL = TypeVar('INTENTION_LEVEL', bound=int)


class Intention(metaclass=ABCMeta):
    """
    对某种意图的结构化描述
    意图可能会有各种分类
    比如:
    - 自然语言
    - 消息类型
    - 事件类型
    - API
    - 命令行

    Intention 如何匹配, 要基于分类来调用对应的 driver
    driver 再用 featuring 获取上下文特征, 用特征来做匹配.
    """
    category: INTENTION_KIND
    level: INTENTION_LEVEL
    priority: float
    args: Dict


class Attentions(metaclass=ABCMeta):
    """
    工程化的注意力机制
    在运行中接受到各种事件, 比如 api/command/设备事件等等
    通过 attentions 机制可以快速定位事件的处理者(reaction)
    """

    def match(self, ctx: Context, category: INTENTION_KIND, arguments: Dict) -> bool:
        pass
