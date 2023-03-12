from abc import ABCMeta, abstractmethod
from typing import Callable, Any, Dict

from larksuiteoapi.service.contact.v3 import Config, Context
from pydantic import BaseModel, Field

from ghoshell.shell.prototypes.lark.messages import ReceiveMessage

# 用户阅读机器人发送的单聊消息后触发此事件。
IM_MESSAGE_READ = "im.message.message_read_v1"

# 首次会话是用户了解应用的重要机会，你可以发送操作说明、配置地址来指导用户开始使用你的应用
P2P_CHAT_CREATE = "p2p_chat_create"

LARK_EVENT_HANDLER = Callable[[Context, Config, Any], None]


class Header(BaseModel):
    event_id: str
    event_type: str
    create_time: str
    token: str
    app_id: str
    tenant_key: str


class Event(BaseModel, metaclass=ABCMeta):
    event_schema: str = Field(default="2.0", alias="schema")
    header: Header
    event: Dict

    @classmethod
    @abstractmethod
    def event_type(cls) -> str:
        pass


class ImMessageReceive(Event):
    """
    机器人接收到用户发送的消息后触发此事件
    """
    event: ReceiveMessage

    @classmethod
    def event_type(cls) -> str:
        return "im.message.receive_v1"
