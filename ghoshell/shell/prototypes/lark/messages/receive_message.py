from typing import List

from pydantic import BaseModel

from ghoshell.shell.prototypes.lark.messages.common import UserInfo


class Mention(BaseModel):
    key: str
    id: UserInfo
    name: str
    tenant_key: str


class Message(BaseModel):
    message_id: str
    root_id: str
    parent_id: str
    create_time: str
    chat_id: str
    chat_type: str
    message_type: str
    content: str
    mentions: List[Mention]


class Sender(BaseModel):
    sender_id: UserInfo
    sender_type: str
    tenant_key: str


class ReceiveMessage(BaseModel):
    sender: Sender
    message: Message
