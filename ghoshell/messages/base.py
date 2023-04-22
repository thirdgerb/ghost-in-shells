from abc import ABCMeta
from typing import ClassVar, Optional, Dict

from pydantic import BaseModel


class Payload(BaseModel):
    """
    消息的弱类型形态,
    kind 是消息的类型
    content 默认提供一个 json 序列化的字段.

    todo: 未来 payload 也需要支持多轮输入聚合. 等有具体场景再研究.
    """
    # 消息体的唯一 ID
    id: str

    # 消息体如果和 Task 挂钩的话, 可以携带 task 的 id
    tid: str

    # body 仍然是一个 1:n:n 的协议
    body: Dict[str, Dict]


class Message(BaseModel, metaclass=ABCMeta):
    """
    消息的强类型形态.
    必须有 KIND 字段用来做反射.
    """

    KIND: ClassVar[str] = ""

    @classmethod
    def from_payload(cls, payload: Payload) -> Optional["Message"]:
        data = payload.body.get(cls.KIND, None)
        if data is None:
            return None
        return cls(**data)

    def join_payload(self, payload: Payload) -> Payload:
        payload.body[self.KIND] = self.dict()
        return payload
