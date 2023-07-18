from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Iterator, ClassVar

from pydantic import BaseModel


class APIResp(BaseModel, metaclass=ABCMeta):
    """
    API 的返回值定义.
    """
    api_caller: ClassVar[str] = ""

    @classmethod
    def call(cls, repo: "APIRepository", args: "APIArgs") -> APIResp:
        """
        强类型约束的语法糖.
        """
        return repo.call(args)


class APIArgs(BaseModel, metaclass=ABCMeta):
    """
    API 的参数类定义.
    """
    api_caller: ClassVar[str] = ""

    @classmethod
    @abstractmethod
    def resp_type(cls) -> Type[APIResp]:
        pass


class APIError(RuntimeError):
    """
    API 接口调用异常.
    """

    def __init__(self, code: int, message: str, suggestion: str = ""):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__()


class APICaller(metaclass=ABCMeta):
    """
    一个标准的 API 的封装.
    """

    @classmethod
    @abstractmethod
    def args_type(cls) -> Type[APIArgs]:
        pass

    @abstractmethod
    def call(self, args: APIArgs) -> APIResp:
        """
        :raise APIError
        """
        pass


class APIRepository(metaclass=ABCMeta):
    """
    存放所有 API 的容器.
    还需要和测试用例结合到一起.
    """

    def call(self, args: APIArgs) -> APIResp:
        api = self.get_api(args.api_caller)
        if api is None:
            raise ImportError(f"api caller {args.api_caller} not found")
        api_type = api.args_type()
        if not isinstance(args, api_type):
            raise ValueError(f"arguments type {type(args)} is not instance of {type(api_type)}")
        return api.call(args)

    @abstractmethod
    def get_api(self, namespace: str) -> APICaller | None:
        pass

    @abstractmethod
    def register_api(self, api: APICaller) -> None:
        pass

    @abstractmethod
    def foreach_api(self) -> Iterator[APICaller]:
        pass
