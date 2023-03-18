from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from ghoshell.ghost.context import IContext


class IOperator(metaclass=ABCMeta):
    """
    Ghost 运行时的算子
    """

    @abstractmethod
    def run(self, ctx: IContext) -> Optional[IOperator]:
        """
        每个算子有自己的运行流程, 运行完后生成下一个算子.
        没有算子的时候, 意味着整个 Runtime 结束了.
        """
        pass
