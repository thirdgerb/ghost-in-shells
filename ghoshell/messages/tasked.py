from typing import Dict, ClassVar

from ghoshell.messages.base import Message


class Tasked(Message):
    """
    内部指令, 将一个任务及其状态作为消息体传输
    通常用于同一个 clone 内部 yielding 类型的任务, 在多个子进程之间交换数据
    也可以在不同的 clone, 不同的 ghost 之间来传递.
    基本原理: tid 都是通过 func(ctx, resolver, args) 来生成的.

    注意: 这里的 status 应该不是 running
    """

    KIND: ClassVar[str] = "tasked"

    resolver: str
    stage: str
    args: Dict
    vars: Dict
    tid: str | None = None
