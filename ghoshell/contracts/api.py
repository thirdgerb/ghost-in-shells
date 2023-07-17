from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Iterator

from pydantic import BaseModel


class API(metaclass=ABCMeta):
    """
    一个标准的 API 的封装.
    """

    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc

    @classmethod
    @abstractmethod
    def arguments_type(cls) -> Type[BaseModel]:
        pass

    @classmethod
    @abstractmethod
    def response_type(cls) -> Type[BaseModel]:
        pass

    @abstractmethod
    def do_call(self, arguments: BaseModel) -> BaseModel | None:
        pass

    def call(self, arguments: Dict) -> Dict | None:
        args = self.arguments_type()(**arguments)
        resp = self.do_call(args)
        if resp is not None:
            return resp.model_dump()
        return None


class APIRepository(metaclass=ABCMeta):
    """
    存放所有 API 的容器.
    还需要和测试用例结合到一起.
    """

    @abstractmethod
    def get_api(self, namespace: str) -> API | None:
        pass

    @abstractmethod
    def register_api(self, api: API) -> None:
        pass

    @abstractmethod
    def foreach_api(self) -> Iterator[API]:
        pass


class APIRepositoryImpl(APIRepository):
    """
    API 仓库的极简实现.
    """

    def __init__(self):
        self._api_map = {}

    def get_api(self, namespace: str) -> API | None:
        return self._api_map.get(namespace, None)

    def register_api(self, api: API) -> None:
        self._api_map[api.name] = api

    def foreach_api(self) -> Iterator[API]:
        for name in self._api_map:
            yield self._api_map[name]
