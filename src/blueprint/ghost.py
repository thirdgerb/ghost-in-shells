from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .io import Input, Output


class Ghost(metaclass=ABCMeta):

    @property
    @abstractmethod
    def soul(self) -> str:
        """
        bot 可能同时存在于很多个空间
        比如对话机器人张三, 它在每一个 IM 里都叫张三, 但每个对话 session 里的张三都不一样.
        soul 就是 "张三" 的意思, 它对于用户而言是唯一的实体, 对于 bot 提供方而言, 成千上万个张三是同一个项目.
        """
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """
        每一个 Ghost 自身会有一个唯一的 id
        用来和同一个 soul 实例化的其它 ghost 相区分.
        soul (1) => ghost (n) => shells (m)
        shell (1) => ghost (1) => soul (1)
        """

    @abstractmethod
    def lock(self) -> bool:
        """
        锁住当前的 ghost, 其它的消息会 pending, 或者返回用户忙
        """
        pass

    @abstractmethod
    def react(self, inpt: Input) -> Output:
        pass
