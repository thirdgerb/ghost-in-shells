from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TypeVar, Dict, Optional

from pydantic import BaseModel

from ghoshell.ghost.context import Context
from ghoshell.ghost.uml import UML

# intention 的类型. 任何类型的 intention 都要有输出 args 的能力. 常见类型有:
# - command : 命令行模式
# - regex: 正则模式, 不过太 low 了
# - nlu: nature language understanding 模式, 主要做意图解析, 并解析出必要的实体.
# - api: 标准的接口调用
INTENTION_KIND = TypeVar('INTENTION_KIND', bound=str)


class IntentionMeta(BaseModel):
    """
    Intention 的元数据, 方便将各种元数据汇总, 用来做全局的判断.
    """
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
    def match(self, ctx: Context) -> Optional[Dict]:
        """
        是否匹配上下文.
        为 None 表示没有匹配成功. 用任何非 none 值都可以表示匹配成功.
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
