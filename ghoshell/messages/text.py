from ghoshell.messages.base import Message


class Text(Message):
    KIND = "text"
    content: str

    def __str__(self):
        return self.content
