from typing import Dict

from pydantic import BaseModel


class CardAction(BaseModel):
    """
    卡片的操作动作.
    """
    value: Dict[str, str]
    tag: str


class CardCallback(BaseModel):
    """
    卡片的回调信息.
    """
    open_id: str
    user_id: str
    open_message_id: str
    open_chat_id: str
    tenant_key: str
    token: str
    action: CardAction
