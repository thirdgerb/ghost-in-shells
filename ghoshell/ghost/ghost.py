from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from ghoshell.contracts import Container
from ghoshell.ghost.io import Input, Output, Message

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
    from ghoshell.ghost.operator import OperationManager, OperationKernel
    from ghoshell.ghost.mindset import Mindset, Thought
    from ghoshell.ghost.session import Session
    from ghoshell.ghost.features import Featuring
    from ghoshell.ghost.attention import Attentions
    from ghoshell.ghost.uml import UML
    from ghoshell.ghost.runtime import Runtime


class Ghost(metaclass=ABCMeta):
    """
    机器人的灵魂, 同一型号的机器人有相同的灵魂.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        bot 可能同时存在于很多个空间
        比如对话机器人张三, 它在每一个 IM 里都叫张三, 但每个对话 session 里的张三都不一样.
        name 就是 "张三" 的意思, 它对于用户而言是唯一的实体, 对于 bot 提供方而言, 成千上万个张三是同一个项目.
        """
        pass

    #
    # @property
    # @abstractmethod
    # def knowledge(self) -> "Memory":
    #     pass

    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def boostrap(self) -> "Ghost":
        """
        初始化, 自我启动.
        """
        pass

    @abstractmethod
    def mindset(self, clone_id: Optional[str] = None) -> "Mindset":
        pass

    @abstractmethod
    def new_clone(self, clone_id: str) -> "Clone":
        """
        从 ghost 实例化一个副本.
        """
        pass

    @abstractmethod
    def new_context(self, _input: "Input") -> "Context":
        """
        初始化一个上下文.
        """
        pass

    @abstractmethod
    def react(self, _input: "Input") -> "Output":
        pass

    @abstractmethod
    async def await_async_input(self) -> "Input":
        pass

    async def async_output(self) -> "Output":
        _input = await self.await_async_input()
        output = self.react(_input)
        return output

    @abstractmethod
    def async_input(self, _input: "Input") -> None:
        pass

    @abstractmethod
    def new_operation_kernel(self) -> "OperationKernel":
        pass


# class Memory(metaclass=ABCMeta):
#     """
#     实例级别的记忆, 长期存在.
#     """
#
#     @abstractmethod
#     def memorize(self, index: str, info: str) -> None:
#         pass
#
#     @abstractmethod
#     def recall(self, index: str, temperature: float = 0, top_k: int = 1) -> List[Tuple[str, float]]:
#         pass


class Config(BaseModel):
    process_max_tasks: int = 20
    process_default_overdue: int = 1800
    process_lock_overdue: int = 30


class Clone(metaclass=ABCMeta):
    """
    Ghost 的一个实例化副本.
    通过 clone_id 来唯一区分.
    """

    @property
    @abstractmethod
    def clone_id(self) -> str:
        pass

    @property
    @abstractmethod
    def ghost_name(self) -> str:
        """
        机器人的"灵魂"，不同的 Ghost 可能使用同样的灵魂，比如"微软小冰"等
        """
        pass

    @property
    @abstractmethod
    def ghost(self) -> Ghost:
        pass

    @property
    @abstractmethod
    def config(self) -> Config:
        pass

    @property
    @abstractmethod
    def root(self) -> "UML":
        pass

    @property
    @abstractmethod
    def session(self) -> "Session":
        pass

        # @property
        # @abstractmethod
        # def memory(self) -> "Memory":
        #     pass
        #
        # @property
        # @abstractmethod
        # def knowledge(self) -> "Memory":
        #     """
        #     ghost knowledge
        #     """

    @property
    @abstractmethod
    def mind(self) -> "Mindset":
        """
        用来获取所有的记忆.
        """
        pass

    @property
    @abstractmethod
    def featuring(self) -> "Featuring":
        """
        从上下文中获取特征.
        特征是和上下文相关的任何信息.
        通常不包含记忆.
        """
        pass

    @property
    @abstractmethod
    def attentions(self) -> "Attentions":
        """
        机器人状态机当前保留的工程化注意力机制
        与算法不同, 注意的可能是命令行, API, 事件等复杂信息.
        """
        pass

    @property
    @abstractmethod
    def runtime(self) -> "Runtime":
        pass

    @abstractmethod
    def lock(self, pid: Optional[str] = None) -> bool:
        """
        锁住一个 clone, 不让它产生新的分身.
        通常只要锁住进程(Process), 而不是锁住 clone
        """
        pass

    @abstractmethod
    def async_input(self, message: Message, process_id: str) -> None:
        pass

    @abstractmethod
    def manage(self, this: "Thought") -> "OperationManager":
        """
        返回上下文的操作工具
        """
        pass

    @abstractmethod
    def finish(self) -> None:
        pass
