from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict

from ghoshell.container import Container
from ghoshell.ghost.io import Input, Output

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
    from ghoshell.ghost.operator import OperationManager, OperationKernel
    from ghoshell.ghost.mindset import Mindset, Thought
    from ghoshell.ghost.session import Session
    from ghoshell.ghost.intention import Attention
    from ghoshell.ghost.url import URL
    from ghoshell.ghost.runtime import Runtime


class Ghost(metaclass=ABCMeta):
    """
    机器人的灵魂. 注意 Ghost 和 Clone 的区别.
    Clone 是机器人的实体, 用来隔离知识/记忆/情感 等后天信息.
    以对话助手为例, 如果对话助手拥有后天增加的长期记忆, 则相互之间应该隔离, 甚至是物理隔离.

    同一批 Clone 拥有相同的 Ghost, 也就是有相同的出厂灵魂. 而且对 Ghost 的修改会影响到所有的 Clone.
    但 Clone 自己会拥有独立的主体, 所以 Clone 理论上也会形成和 Ghost 的区别.

    Ghost 和 Clone 两个抽象的划分是为了解决个性化问题.
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

    @abstractmethod
    def mindset(self, clone_id: Optional[str] = None) -> "Mindset":
        """
        Ghost 的思维模式.
        注意, Clone 也会有 Mindset, 而一定会有一个 Ghost Mindset 用来做初始化.
        有点像 "class" 的 "extend"
        """
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
    def respond(self, _input: "Input") -> Optional["Output"]:
        """
        完成一轮的响应. 要支持没有任何响应.
        """
        pass

    @abstractmethod
    def async_input(self, _input: "Input") -> None:
        """
        向 Ghost 发送一个异步的输入消息.
        对于 AsyncGhost, 只有用 await_async_input 才能获取到这个消息.
        对于只能响应同步消息的 Ghost, 则需要用同步机制来响应.
        AsyncGhost 是可以用来做发布时间调度的.
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


class AsyncGhost(Ghost, metaclass=ABCMeta):
    """
    可以响应异步消息的 Ghost
    """

    @abstractmethod
    async def await_async_input(self, clone_id: str | None) -> "Input":
        """
        Ghost 需要拥有一个异步输入的消息队列
        可以从这个队列里拿到异步的输入信息.
        基于对 python 的理解, 将它定义成可阻塞的单次获取方法.
        要实现并发, 则需要用多线程等办法, 平行处理多个异步输入.

        这个队列必须是 clone 级别的, 需要实现好时序. 避免分布式系统出现 "脑裂".
        假设可以通过传入 clone_id 来指定消息队列.
        """
        pass

    @abstractmethod
    def ack_async_input(self, _input: "Input", success: bool) -> None:
        """
        await_async_input 拿到消息时, 仍然可能因为阻塞等原因无法执行消息.
        为了防止 "脑裂", 真正的异步input 队列 应该是 clone 级别的, 应该在出消息时有加锁动作, 防止多个消息输出到多个实例.
        没有 ack 的话, 就无法重新激活队列, 也无法判断是否应该删除队头的信息.

        实际的 Ghost 可能有 ack 机制, 也可能没有. 毕竟不是都要实现 at least once
        所以这个接口要根据实际情况设计.
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
    def ghost(self) -> Ghost:
        pass

    @property
    @abstractmethod
    def container(self) -> "Container":
        """
        保证每一层都有自己的 container
        clone 层的 container 通常直接就是 ghost 的
        """
        pass

    @property
    @abstractmethod
    def config(self) -> Dict:
        """
        返回一个 Clone 的默认配置.
        这个配置的协议应该与具体的 prototype, 或者 framework 提供的类一致.
        """
        pass

    @property
    @abstractmethod
    def root(self) -> "URL":
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
    def mindset(self) -> "Mindset":
        """
        用来获取所有的记忆.
        """
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
    def attentions(self) -> "Attention":
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
    def manage(self, this: "Thought") -> "OperationManager":
        """
        返回上下文的操作工具
        为什么这个在 Clone 上, 而不封装到 Ctx
        就是为了让 Clone 可以对外暴露一个超级干预能力.
        """
        pass

    @abstractmethod
    def finish(self) -> None:
        pass
