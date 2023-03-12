from typing import Dict

from pydantic import BaseModel


class UML(BaseModel):
    think: str = ""
    state: str = ""
    args: Dict = {}


UniformMindLocator = UML
