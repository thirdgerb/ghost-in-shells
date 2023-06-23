from __future__ import annotations

import json
from abc import ABCMeta, abstractmethod
from typing import List, Dict, ClassVar

from pydantic import BaseModel, Field


class OpenAIFuncSchema:
    """
    openai 对 function 的定义策略.
    """

    def __init__(self, name: str, desc: str | None = None, parameters_schema: Dict | None = None):
        self.name = name
        self.desc = desc
        if parameters_schema is None:
            parameters_schema = BaseModel.schema()
        if "title" in parameters_schema:
            del parameters_schema["title"]
        self.parameters_schema = parameters_schema

    def dict(self) -> Dict:
        result = {"name": self.name}
        if self.desc is not None:
            result["description"] = self.desc
        result["parameters"] = self.parameters_schema
        return result


class OpenAIChatMsg(BaseModel):
    ROLE_SYSTEM: ClassVar[str] = "system"
    ROLE_USER: ClassVar[str] = "user"
    ROLE_ASSISTANT: ClassVar[str] = "assistant"
    ROLE_FUNCTION: ClassVar[str] = "function"

    role: str = Field(enum={"system", "user", "assistant", "function"})
    name: str | None = None
    content: str | None = None

    function_call: Dict | None = None

    def to_message(self) -> Dict:
        data = self.dict(include={"role", "content", "name", "function_call"})
        result = {}
        for key in data:
            value = data[key]
            if value is None:
                continue
            result[key] = value
        return result


class OpenAIFuncCalled(BaseModel):
    # function name
    name: str
    # arguments json
    arguments: Dict


class OpenAIChatChoice(BaseModel):
    index: int
    message: Dict
    finish_reason: str

    def get_function_called(self) -> Dict | None:
        return self.message.get("function_call", None)

    def get_role(self) -> str | None:
        return self.message.get("role", None)

    def get_content(self) -> str | None:
        return self.message.get("content", None)

    def as_func_called(self) -> OpenAIFuncCalled | None:
        called = self.get_function_called()
        if called is None:
            return None
        arguments = called.get("arguments")
        return OpenAIFuncCalled(
            name=called.get("name"),
            arguments=json.loads(arguments),
        )

    def as_chat_msg(self) -> OpenAIChatMsg | None:
        content = self.get_content()
        role = self.get_role()
        if content is None or role == OpenAIChatMsg.ROLE_FUNCTION:
            return None
        return OpenAIChatMsg(
            role=role,
            content=content,
        )


class OpenAIChatResponse(BaseModel):
    id: str
    object: str
    created: int
    choices: List[OpenAIChatChoice]
    usage: Dict


class OpenAIChatCompletion(metaclass=ABCMeta):

    @abstractmethod
    def chat_completion(
            self,
            session_id: str,
            chat_context: List[OpenAIChatMsg],
            functions: List[OpenAIFuncSchema] | None = None,
            function_call: str = "",
            config_name: str = "",  # 选择哪个预设的配置
    ) -> OpenAIChatChoice:
        pass
