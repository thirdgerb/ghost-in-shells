from __future__ import annotations

from typing import Dict, Optional, List

from pydantic import BaseModel

from ghoshell.ghost.uml import UML


class Message(BaseModel):
    """
    归一化的消息体.
    ghost 应该定义出自己的消息体系.
    """

    # 所有的消息自身需要有唯一 id.
    id: str = ""

    # 与任务对应的 tid, 输入消息对标的是上一个消息
    # 输出消息对标的是生成的场景.
    tid: str = ""

    # 如果是个消息
    text: str = ""


class Trace(BaseModel):
    # shell 的 id. 对齐 shell 的 session.
    # 举个例子, 如果 shell 是一个 IM
    # 则 shell id 最好就是 IM 的 chat_id
    shell_id: str = ""
    # shell 的类型
    shell_kind: str = ""
    # session 的唯一 id.
    # 理论上不同的 shell 之间的 session_id 也不能混合.
    # 只有在一个 shell 对应唯一的一个 ghost 时, 才可以将两者完全互通.
    session_id: str = ""
    # 对话的进程 id. 一个 session 可以同时运行多个进程. 默认为空.
    process_id: str = ""
    # 输入信息的主体
    subject_id: str = ""


class Input(BaseModel):
    """
    ghost 的输入
    """

    # 传入的事件数据. 应该需要做归一化处理.
    message: Message

    # 输入的 trace.
    trace: Trace

    # 传入 shell 侧携带的上下文信息, shell 侧定义的协议
    # 如果 ghost 希望理解 shell 的话, 可以主动处理这部分上下文
    shell_env: Dict = None

    # ghost 约定的上下文协议. 可以传入额外的信息
    ghost_env: Dict = None

    # 请求相关的场景. 如果 ghost 是初始化, 则用 UML 定位场景.
    uml: Optional[UML] = None
    # 如果是无状态请求, 则任何行为不会变更 ghost 状态.

    stateless: bool = False
    # 异步消息, 回复的消息也应该是异步的.
    is_async: bool = False


class Output(BaseModel):
    """
    ghost 的输出.
    """
    # 关联到的输入
    input: Input
    # 运行时拿到的各种动作.
    messages: List[Message] = []

    # 传给 shell 的上下文信息, shell 侧定义的协议
    # ghost 理解 shell 的情况下, 可以用这种方式去控制 shell
    shell_env: Dict = {}

    # ghost 约定的上下文协议.
    # shell 如果理解 ghost 的话, 可以主动处理这部分信息.
    ghost_env: Dict = {}
