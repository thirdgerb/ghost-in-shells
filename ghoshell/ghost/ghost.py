from abc import ABCMeta, abstractmethod

from ghoshell.ghost.io import Input, Output, Trace
from ghoshell.ghost.mindset import Mindset


class Ghost(metaclass=ABCMeta):

    @property
    @abstractmethod
    def name(self) -> str:
        """
        bot 可能同时存在于很多个空间
        比如对话机器人张三, 它在每一个 IM 里都叫张三, 但每个对话 session 里的张三都不一样.
        soul 就是 "张三" 的意思, 它对于用户而言是唯一的实体, 对于 bot 提供方而言, 成千上万个张三是同一个项目.
        """
        pass

    def boostrap(self) -> None:
        """
        初始化, 启动
        """
        pass

    @abstractmethod
    def mindset(self, trace: Trace) -> Mindset:
        """
        根据 Trace 来生成 Mindset, 可以用来注册 Thinking
        为什么要根据 Trace 来注册呢?
        因为这意味着可以定制会话级的能力, 能力之间相互隔离.
        如果每个用户都有自己的小助手的话, 他们的 mindset 就可以不一样.
        当然, 全部注册到全局, 用 thinking 的 id 区隔也是一种解法.
        只不过可理解性会差很多.
        """
        pass

    @abstractmethod
    def react(self, inpt: Input) -> Output:
        """
        核心方法: 处理输入 inpt
        """
