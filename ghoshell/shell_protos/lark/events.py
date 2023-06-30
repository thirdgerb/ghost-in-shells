# from typing import Callable, Any, Dict, List, Type
#
# from larksuiteoapi.service.contact.v3 import Config, Context
# from pydantic import BaseModel, Field
#
# from ghoshell.shell.prototypes.lark.messages import ReceiveMessage
#
# IM_MESSAGE_RECEIVE = "im.message.receive_v1"
# # 用户阅读机器人发送的单聊消息后触发此事件。
# IM_MESSAGE_READ = "im.message.message_read_v1"
#
# # 首次会话是用户了解应用的重要机会，你可以发送操作说明、配置地址来指导用户开始使用你的应用
# P2P_CHAT_CREATE = "p2p_chat_create"
#
# LARK_EVENT_HANDLER = Callable[[Context, Config, Any], None]
#
#
# class LarkEventCaller:
#     """
#     对 lark 消息的基本封装.
#     """
#
#     def __init__(self, ctx: Context, conf: Config, event: Dict):
#         self.ctx = ctx
#         self.conf = conf
#         self.event = event
#         self.event_type = event.get("header", {}).get("event_type", "")
#
#
# class Header(BaseModel):
#     """
#     实现 lark 的 event
#     这是 lark event.header
#     """
#     event_id: str
#     event_type: str
#     create_time: str
#     token: str
#     app_id: str
#     tenant_key: str
#
#
# class Event(BaseModel):
#     """
#     lark 的事件
#     """
#
#     event_schema: str = Field(default="2.0", alias="schema")
#     header: Header
#     event: Dict
#
#     @classmethod
#     def event_type(cls) -> str:
#         return ""
#
#
# class ImMessageReceive(Event):
#     """
#     机器人接收到用户发送的消息后触发此事件
#     """
#     event: ReceiveMessage
#
#     @classmethod
#     def event_type(cls) -> str:
#         return IM_MESSAGE_RECEIVE
#
#
# # Event 列表
# EVENTS: List[Type[Event]] = [
#     ImMessageReceive,
# ]
#
# # Event 字典
# EVENTS_MAP: Dict[str, Type[Event]] = {e.event_type(): e for e in EVENTS}
