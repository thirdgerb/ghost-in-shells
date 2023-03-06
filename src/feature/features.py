from typing import Dict

from src.blueprint import Feature, FEAT_KEY

FEAT_TEXT: FEAT_KEY = "text"
FEAT_CMD: FEAT_KEY = "command"


class Text(Feature):
    """
    最常见的特征, 从上下文中获得文字.
    """
    keyword = FEAT_TEXT

    text: str

    def __init__(self, text=""):
        self.text = text


class Command(Feature):
    """
    从上下文中获得了一个命令
    """
    keyword = FEAT_CMD

    name: str
    args: Dict
    options: Dict

    def __init__(self, name: str, args: Dict, options: Dict):
        self.name = name
        self.args = args
        self.options = options
