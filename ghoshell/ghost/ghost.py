from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List

from ghoshell.container import Container
from ghoshell.messages import Input, Output

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
    from ghoshell.ghost.mindset.operator import OperationKernel
    from ghoshell.ghost.mindset import Mindset
    from ghoshell.ghost.mindset.focus import Focus
    from ghoshell.ghost.url import URL
    from ghoshell.ghost.mindset.focus import Focus
    from ghoshell.ghost.memory import Memory


class Ghost(metaclass=ABCMeta):
    """
    机器人的灵魂. 注意 Ghost 和 Clone 的区别.
    Clone 是机器人的实体, 用来隔离知识/记忆/情感 等后天信息.
    以对话助手为例, 如果对话助手拥有后天增加的长期记忆, 则相互之间应该隔离, 甚至是物理隔离.

    同一批 Clone 拥有相同的 Ghost, 也就是有相同的出厂灵魂. 而且对 Ghost 的修改会影响到所有的 Clone.
    但 Clone 自己会拥有独立的主体, 所以 Clone 理论上也会形成和 Ghost 的区别.

    Ghost 和 Clone 两个抽象的划分是为了解决个性化问题.
    """
    AS_SHELL_KIND: ClassVar[str] = "ghost"

    @property
    @abstractmethod
    def name(self) -> str:
        """
        bot 可能同时存在于很多个空间
        比如对话机器人张三, 它在每一个 IM 里都叫张三, 但每个对话 session 里的张三都不一样.
        name 就是 "张三" 的意思, 它对于用户而言是唯一的实体, 对于 bot 提供方而言, 成千上万个张三是同一个项目.
        """
        pass

    def app_path(self) -> str:
        pass

    @property
    @abstractmethod
    def container(self) -> "Container":
        """
        通过 Container 把和 Ghost 无关,
        又需要通过 Ghost 传递的各种组件包起来.
        这是一种解耦的思路.
        不需要我在 Ghost 里定义 Logger 之类的组件.
        """
        pass

    # @property
    # @abstractmethod
    # def knowledge(self) -> "Memory":
    #     pass

    @abstractmethod
    def boostrap(self) -> "Ghost":
        """
        对 Ghost 进行初始化.
        """
        pass

    @property
    @abstractmethod
    def mindset(self) -> "Mindset":
        pass

    @property
    @abstractmethod
    def focus(self) -> "Focus":
        """
        机器人状态机当前保留的工程化注意力机制
        与算法不同, 注意的可能是命令行, API, 事件等复杂信息.
        """
        pass

    @property
    @abstractmethod
    def memory(self) -> "Memory":
        pass

    @abstractmethod
    def new_clone(self, clone_id: str) -> "Clone":
        """
        从 ghost 实例化一个副本 clone.
        但 clone 是否能从 ghost 中产生呢?
        这只是表示了一个启动流程.
        """
        pass

    @abstractmethod
    def new_context(self, _input: "Input") -> "Context":
        """
        为了相应输入, 初始化一个上下文.
        """
        pass

    @abstractmethod
    def respond(self, _input: "Input") -> List["Output"] | None:
        """
        完成一轮的响应. 要支持没有任何响应.
        """
        pass

    @abstractmethod
    def new_operation_kernel(self) -> "OperationKernel":
        """
        Ghost 需要提供一个 Kernel 能够运转所有的 runtime 指令 (Operator)
        而这个 kernel 是可以按需重构的.
        我理解不同的机器人, 可能会有不同的运行时方案, 这里做出抽象方便调整.
        但 ghoshell 只会实现唯一的一个 kernel
        """
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

class Clone(metaclass=ABCMeta):
    """
    Ghost 的一个实例化副本. 两个目的:
    1. 通过 clone_id 来隔离不同的 Ghost 实例, 主要是个性化思维和上下文记忆. 至于 Runtime 通过 Session 来隔离.
    2. 让 clone 作为一个 API, 可以对外暴露 Ghost 的 Runtime, 使之可以通过命令要求, 解释自己的状态.

    Clone 长期迭代目标是完善 2, 也就是越来越强的干预和自解释能力.
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
    def root(self) -> "URL":
        pass

    @property
    @abstractmethod
    def mindset(self) -> "Mindset":
        """
        用来获取所有的记忆.
        """
        pass

    @property
    @abstractmethod
    def memory(self) -> "Memory":
        pass

    # @property
    # @abstractmethod
    # def featuring(self) -> "Featuring":
    #     """
    #     从上下文中获取特征.
    #     特征是和上下文相关的任何信息.
    #     通常不包含记忆.
    #     """
    #     pass

    @property
    @abstractmethod
    def focus(self) -> "Focus":
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
