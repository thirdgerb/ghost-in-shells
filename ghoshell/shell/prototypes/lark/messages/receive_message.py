from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json

from .common import UserInfo, Header


@dataclass_json
@dataclass
class Mention:
    key: str
    id: UserInfo
    name: str
    tenant_key: str


@dataclass_json
@dataclass
class Message:
    message_id: str
    root_id: str
    parent_id: str
    create_time: str
    chat_id: str
    chat_type: str
    message_type: str
    content: str
    mentions: List[Mention]


@dataclass_json
@dataclass
class Sender:
    sender_id: UserInfo
    sender_type: str
    tenant_key: str


@dataclass_json
@dataclass
class ReceiveMessage:
    @dataclass_json
    @dataclass
    class ReceiveMessageEvent:
        sender: Sender
        message: Message

    schema: str
    header: Header
    event: ReceiveMessageEvent
