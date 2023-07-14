# from typing import List
#
# from pydantic import BaseModel
#
#
# class UserInfo(BaseModel):
#     union_id: str = ""
#     user_id: str = ""
#     open_id: str = ""
#
#
# class Mention(BaseModel):
#     key: str = ""
#     id: UserInfo = UserInfo()
#     name: str = ""
#     tenant_key: str = ""
#
#
# class Message(BaseModel):
#     message_id: str = ""
#     root_id: str = ""
#     parent_id: str = ""
#     create_time: str = ""
#     chat_id: str = ""
#     chat_type: str = ""
#     message_type: str = ""
#     content: str = ""
#     mentions: List[Mention] = []
