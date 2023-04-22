from typing import List

from pydantic import BaseModel

from ghoshell.ghost import Intention


class TextClassifier(Intention):
    KIND = "text_classifier"

    class Config(BaseModel):
        description: str = ""
        examples: List[str] = []

    class Result(BaseModel):
        prop: float

    config: Config
    matched: Result | None = None
