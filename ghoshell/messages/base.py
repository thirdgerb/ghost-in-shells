from __future__ import annotations

from abc import ABCMeta
from typing import ClassVar, Optional, Dict

from pydantic import BaseModel, Field


class Payload(BaseModel):
    """
    消息的弱类型形态,
    kind 是消息的类型
    content 默认提供一个 json 序列化的字段.

    todo: 未来 payload 也需要支持多轮输入聚合. 等有具体场景再研究.
    """

    # 消息体如果和 Task 挂钩的话, 可以携带 task 的 id
    tid: str = ""

    # body 仍然是一个 1:n:n 的协议
    body: Dict[str, Dict] = Field(default_factory=lambda: {})


class Message(BaseModel, metaclass=ABCMeta):
    """
    消息的强类型形态.
    必须有 KIND 字段用来做反射.
    """

    KIND: ClassVar[str] = ""

    @classmethod
    def read(cls, payload: Payload) -> Optional["Message"]:
        data = payload.body.get(cls.KIND, None)
        if data is None:
            return None
        return cls(**data)

    def as_payload(self, tid: str = "") -> Payload:
        p = Payload(tid=tid)
        self.join(p)
        return p

    def as_payload_dict(self, tid: str = "") -> Dict:
        return dict(
            tid=tid,
            body={self.KIND: self.model_dump()}
        )

    def join(self, payload: Payload) -> bool:
        return self.join_body(payload.body)

    def join_body(self, body: Dict) -> bool:
        if self.KIND in body:
            return False
        body[self.KIND] = self.model_dump()
        return True


class Signal(Message):
    KIND: ClassVar[str] = "signal"
    QUIT_CODE: ClassVar[int] = 0

    code: int

    @classmethod
    def quit(cls) -> "Signal":
        return Signal(code=Signal.QUIT_CODE)
