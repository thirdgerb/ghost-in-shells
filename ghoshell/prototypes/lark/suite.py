# from typing import List
#
# from larksuiteoapi import Config
#
# from ghoshell.ghost import Payload
#
#
# class LarkSuite:
#
#     def __init__(self, config: Config):
#         self.config = config
#
#     def send_message(self, receive_id: str, msg: Payload) -> None:
#         replies: List[Messenger] = []
#         if msg.content:
#             replies.append(Messenger(
#                 receive_id=receive_id,
#             ))
