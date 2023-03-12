from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from ghoshell.ghost.context import IContext


class IOperator(metaclass=ABCMeta):
    """
    runtime 运行时的算子
    """

    @abstractmethod
    def run(self, ctx: IContext) -> Optional[IOperator]:
        pass
