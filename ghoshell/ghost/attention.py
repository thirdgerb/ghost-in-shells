from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TypeVar, Optional, List, Any, ClassVar

from pydantic import BaseModel

from ghoshell.ghost.context import Context
from ghoshell.ghost.uml import UML

# intention 的类型. 任何类型的 intention 都要有输出 args 的能力. 常见类型有:
# - command : 命令行模式
# - regex: 正则模式, 不过太 low 了
# - nlu: nature language understanding 模式, 主要做意图解析, 并解析出必要的实体.
# - api: 标准的接口调用
INTENTION_KIND = TypeVar('INTENTION_KIND', bound=str)


class Intention(BaseModel, metaclass=ABCMeta):
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
    KIND: ClassVar[str] = ""

    uml: UML
    config: Any
    result: Any | None = None

    def with_matched(self, matched: Any) -> "Intention":
        data = self.dict()
        data["matched"] = matched
        return self.__class__(**data)


class Attentions(metaclass=ABCMeta):
    """
    工程化的注意力机制
    在运行中接受到各种事件, 比如 api/command/设备事件等等
    通过 attentions 机制可以快速定位事件的处理者(task resolver => Thinking)
    """

    @abstractmethod
    def kinds(self) -> List[str]:
        pass

    @abstractmethod
    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        pass

    @abstractmethod
    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        pass

    @abstractmethod
    def register(self, *intentions: Intention) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        提醒记得清除垃圾.
        """
        pass
