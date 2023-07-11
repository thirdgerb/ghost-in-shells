from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import ClassVar, Any

from pydantic import BaseModel

from ghoshell.ghost.context import Context


class Memo(BaseModel, metaclass=ABCMeta):
    """
    一个记忆单元. 是一个数据结构.
    关键是要能提供 index 信息.
    """

    KIND: ClassVar[str] = ""

    @abstractmethod
    def index(self) -> Any:
        pass

    def fetch(self, ctx: Context) -> Memo | None:
        return ctx.clone.memory.recall(self.KIND, self.index())


class MemoryDriver(metaclass=ABCMeta):
    """
    memory 的驱动.
    Memory 作为一个通用的 interface, 可以保存各种不同类型的记忆数据.
    每一种记忆数据都依赖一个 Driver 来读写.
    """

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def recall(self, index: Any) -> Memo | None:
        pass

    @abstractmethod
    def save(self, memo: Memo) -> None:
        pass


class Memory(metaclass=ABCMeta):
    """
    Memory 模块.
    """

    @abstractmethod
    def clone(self, clone_id: str) -> Memory:
        """
        根据 clone_id 得到一个 memory 的分身.
        使得 clone 的记忆也存在某种 继承/重写 机制
        """
        pass

    @abstractmethod
    def memorize(self, memo: Memo) -> None:
        """
        记住一个 Memo
        """
        pass

    @abstractmethod
    def recall(self, kind: str, index: Any) -> Memo | None:
        """
        尝试回忆一个 Memo
        """
        pass

    @abstractmethod
    def register(self, driver: MemoryDriver) -> None:
        """
        注册一个 Driver.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
