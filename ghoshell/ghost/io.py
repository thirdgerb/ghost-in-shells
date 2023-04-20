from __future__ import annotations

from typing import Dict, Optional, List

from pydantic import BaseModel, Field

from ghoshell.ghost.uml import UML
from ghoshell.messages import *


class Trace(BaseModel):
    # 消息对应的 clone id
    # 可以为空, 为空的话 ghost 应该有办法根据其它字段匹配一个.
    clone_id: str = ""

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
    # 通常是用户.
    subject_id: str = ""


class Input(BaseModel):
    """
    ghost 的输入
    """
    id: str

    # 传入的事件数据. 应该需要做归一化处理.
    payload: Payload

    # 输入的 trace.
    trace: Trace = Field(default_factory=lambda: Trace())

    # 传入 shell 侧携带的上下文信息, shell 侧定义的协议
    # 如果 ghost 希望理解 shell 的话, 可以主动处理这部分上下文
    shell_env: Dict = None

    # ghost 约定的上下文协议. 可以传入额外的信息
    ghost_env: Dict = None

    # 请求相关的场景. 如果 ghost 是初始化, 则用 UML 定位场景.
    uml: Optional[UML] = None

    # 如果是无状态请求, 则这个消息预期不会变更 ghost 的状态.
    # 任何与状态相关的动作都不应该最终保存.
    # 这一点不容易实现, 因为不是所有的 IO 都通过 Runtime 来控制.
    stateless: bool = False

    # 异步消息, 回复的消息也应该是异步的.
    is_async: bool = False


class Output(BaseModel):
    """
    ghost 的输出.
    """
    #  输出的唯一 id, 用来记录 output 的 批次.
    id: str

    # 关联到的输入
    input: Input

    # 输出的路径. 如果为 None 的话, 则默认是 input 的 trace 作为输出的 trace.
    # 这是因为, 输出给 shell 的消息, 不一定和输入消息对应.
    # 这种复杂的 feature 并不都需要实现.
    trace: Optional[Trace] = None

    # 运行时拿到的各种动作.
    payloads: List[Payload] = Field(default_factory=lambda: [])

    # 传给 shell 的上下文信息, shell 侧定义的协议
    # ghost 理解 shell 的情况下, 可以用这种方式去控制 shell
    shell_env: Dict = Field(default_factory=lambda: {})

    # ghost 约定的上下文协议.
    # shell 如果理解 ghost 的话, 可以主动处理这部分信息.
    ghost_env: Dict = Field(default_factory=lambda: {})

    @classmethod
    def new(cls, _input: Input) -> Output:
        return Output(
            input=Input(**_input.dict()),
        )

    def output_trace(self) -> Trace:
        return self.trace if self.trace is not None else self.input.trace
