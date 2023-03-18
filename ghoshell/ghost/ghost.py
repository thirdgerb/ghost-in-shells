from abc import ABCMeta, abstractmethod

from ghoshell.ghost.io import Input, Output


class IGhost(metaclass=ABCMeta):

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
    async def react(self, inpt: Input) -> Output:
        """
        核心方法: 处理输入 inpt
        """
