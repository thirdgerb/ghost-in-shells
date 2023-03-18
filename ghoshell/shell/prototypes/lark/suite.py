from typing import List

from larksuiteoapi import Config

from ghoshell.ghost import Message


class LarkSuite:

    def __init__(self, config: Config):
        self.config = config

    def send_message(self, receive_id: str, msg: Message) -> None:
        replies: List[Messenger] = []
        if msg.text:
            replies.append(Messenger(
                receive_id=receive_id,
            ))
