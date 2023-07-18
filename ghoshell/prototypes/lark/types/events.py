from __future__ import annotations

from abc import ABCMeta
from typing import Dict, ClassVar, List

from pydantic import BaseModel, Field

from ghoshell.prototypes.lark.types.user import UserIds


class EventHeader(BaseModel):
    """
    事件头.
    """
    event_id: str = Field(description="事件的唯一标识")
    token: str = Field(description="Verification Token")
    create_time: str = Field(description="事件发送的时间，一般近似于事件发生的时间")
    event_type: str = Field(description="事件类型")
    tenant_key: str
    app_id: str


class EventBody(BaseModel, metaclass=ABCMeta):
    """
    事件体的类型约束.
    """
    event_type: ClassVar[str] = ""


class Sender(BaseModel):
    """
    事件发送者. 部分事件包含.
    """
    # "sender": {
    #     "sender_id": {
    #         "union_id": "on_8ed6aa67826108097d9ee143816345",
    #         "user_id": "e33ggbyz",
    #         "open_id": "ou_84aad35d084aa403a838cf73ee18467"
    #     },
    #     "sender_type": "user",
    #     "tenant_key": "736588c9260f175e"
    # }
    sender_id: UserIds
    sender_type: str = Field(description="发送者类型, 目前只支持 user", default="user")
    tenant_key: str = Field(description="tenant key，为租户在飞书上的唯一标识，用来换取对应的tenant_access_token，"
                                        "也可以用作租户在应用里面的唯一标识")


class LarkEvent(BaseModel):
    """
    Lark 的事件.
    """
    schema: str = Field(description="事件的版本。v1.0 版本的事件，无此字段")
    header: EventHeader
    event: Dict


class Mention(BaseModel):
    key: str
    id: UserIds
    name: str
    tenant_key: str


class ReceiveMessage(BaseModel):
    """
    接受到的消息体, 要根据 message_type 去匹配真实的消息.
    """
    message_id: str
    root_id: str
    parent_id: str
    create_time: str
    chat_id: str
    chat_type: str
    message_type: str
    content: str
    mentions: List[Mention]


class IMMessageReceiveV1(EventBody):
    """
    支持的应用类型: 自建应用, 商店应用
    权限要求: 开启任一权限即可
    获取用户在群组中@机器人的消息
    接收群聊中@机器人消息事件
    获取群组中所有消息
    读取用户发给机器人的单聊消息
    获取用户发给机器人的单聊消息
    """
    event_type: ClassVar = "im.message.receive_v1"
    sender: Sender
    message: ReceiveMessage
