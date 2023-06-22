from __future__ import annotations

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
    content: str | None = None
    name: str | None = None

    function_call: Dict | None = None

    def to_message(self) -> Dict:
        data = self.dict(include={"role", "content", "name"})
        result = {}
        for key in data:
            value = data[key]
            if value is None:
                continue
            result[key] = value
        return result


class OpenAIChatChoice(BaseModel):
    index: int
    message: Dict
    finish_reason: str

    def get_function_called(self) -> str | None:
        if self.message.get("role", None) != OpenAIChatMsg.ROLE_FUNCTION:
            return None
        return self.message.get("function_call", {}).get("name", None)

    def get_function_params(self) -> Dict | None:
        if self.message.get("role", None) != OpenAIChatMsg.ROLE_FUNCTION:
            return None
        called = self.message.get("function_call", None)
        if called is None:
            return None
        params = self.message.copy()
        del (params["function_call"])
        return params

    def get_role(self) -> str | None:
        return self.message.get("role", None)

    def get_content(self) -> str | None:
        return self.message.get("content", None)

    def as_chat_msg(self) -> OpenAIChatMsg | None:
        content = self.get_content()
        role = self.get_role()
        if content is None or role is None:
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
            function_call: str = "none",
            config_name: str = "",  # 选择哪个预设的配置
    ) -> OpenAIChatChoice:
        pass
