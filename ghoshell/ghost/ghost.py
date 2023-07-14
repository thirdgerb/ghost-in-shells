from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List

from ghoshell.container import Container
from ghoshell.messages import Input, Output

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
    from ghoshell.ghost.mindset import OperationKernel
    from ghoshell.ghost.mindset import Mindset
    from ghoshell.ghost.mindset import Focus
    from ghoshell.url import URL
    from ghoshell.ghost.mindset import Focus
    from ghoshell.ghost.memory import Memory


class Ghost(metaclass=ABCMeta):
    """
    机器人的灵魂. 一个灵魂 (Ghost) 可能有很多个相互独立的分身 (Clone)
    Clone 相当于机器人的个体, 这个概念用来隔离知识/记忆/情感 等 `后天` 的信息.

    以对话助手为例, 每个用户的对话助手互相之间的知识是不相通的.
    如果对话助手拥有后天增加的长期记忆, 则相互之间应该隔离, 甚至是物理隔离.

    同一批 Clone 拥有相同的 Ghost, 也就是有相同的出厂灵魂. 而且对 Ghost 的修改会影响到所有的 Clone.
    但 Clone 自己会拥有独立的主体, 所以 Clone 理论上也会形成和 Ghost 的区别.

    Ghost 和 Clone 两个抽象的划分是为了解决个性化问题.
    """

    # 一个常量, 当 ghost 与 ghost 通讯时, 发送者的 ghost 也就成了 shell. 因此需要有一个常量来标记.
    AS_SHELL_KIND: ClassVar[str] = "ghost"

    # ---- 系统级的参数 ---- #

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
    def config_path(self) -> str:
        """
        系统启动时的配置文件路径.
        各种系统级的配置文件可以保存在这个路径下.
        """
        pass

    @property
    @abstractmethod
    def runtime_path(self) -> str:
        """
        系统运行时文件路径
        在这个路径里保存各种运行时的数据, 比如日志.
        """
        pass

    # ---- 启动类方法 ---- #

    @abstractmethod
    def boostrap(self) -> "Ghost":
        """
        对 Ghost 进行初始化. 没有运行 bootstrap 方法的 ghost 没有启动.
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

    # ---- 运行时方法. ---- #

    @abstractmethod
    def respond(self, _input: "Input") -> List["Output"] | None:
        """
        完成一轮的响应. 要支持没有任何响应.
        """
        pass

    # ---- 全局组件  ---- #

    @property
    @abstractmethod
    def container(self) -> "Container":
        """
        通过 Container 提供面向 interface 的容器.
        这是一种解耦的思路. 我们在设计时只需要向 Container 申请 interface, 就可以拿到 implemented.
        """
        pass

    @property
    @abstractmethod
    def mindset(self) -> "Mindset":
        """
        Ghost 固有的思维集合. 这个思维集合会给 Clone 继承.
        """
        pass

    @property
    @abstractmethod
    def focus(self) -> "Focus":
        """
        机器人状态机当前保留的工程化注意力机制
        与 LLM 算法不同, 注意的可能是 command line, API, event, signal 等工程化的数据.
        """
        pass

    @property
    @abstractmethod
    def memory(self) -> "Memory":
        """
        对记忆能力的工程化封装.
        每种不同类型的 Memory 实现, 都可以基于这种 interface 来封装.
        常见的 memory 机制:
        1. KV
        2. Embedding Index
        3. fulltext index
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
        """
        每个 Clone 的全局唯一 id.
        """
        pass

    @property
    @abstractmethod
    def ghost(self) -> Ghost:
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

    @property
    @abstractmethod
    def focus(self) -> "Focus":
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
