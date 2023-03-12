from typing import Callable, Any

from larksuiteoapi.service.contact.v3 import Config, Context

# 机器人接收到用户发送的消息后触发此事件
IM_MESSAGE_RECEIVE = "im.message.receive_v1"
# 用户阅读机器人发送的单聊消息后触发此事件。
IM_MESSAGE_READ = "im.message.message_read_v1"

# 首次会话是用户了解应用的重要机会，你可以发送操作说明、配置地址来指导用户开始使用你的应用
P2P_CHAT_CREATE = "p2p_chat_create"

LARK_EVENT_HANDLER = Callable[[Context, Config, Any], Any]

# HANDLER =
#
# def wrapper()
#
# handlers = {
#     IM_MESSAGE_RECEIVE: ""
#
# }
