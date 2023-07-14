from typing import List

from pydantic import BaseModel

from ghoshell.ghost import Intention


class TextClassifier(Intention):
    """
    文本分类.
    """
    kind = "text_classifier"

    class Config(BaseModel):
        description: str = ""
        examples: List[str] = []

    class Result(BaseModel):
        prop: float

    config: Config
    params: Result | None = None
