from typing import List

from pydantic import BaseModel

from ghoshell.ghost import Intention


class TextClassifier(Intention):
    """
    文本分类.
    """
    kind = "text_classifier"

    # TODO[pydantic]: The `Config` class inherits from another class, please create the `model_config` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    class Config(BaseModel):
        description: str = ""
        examples: List[str] = []

    class Result(BaseModel):
        prop: float

    config: Config
    params: Result | None = None
