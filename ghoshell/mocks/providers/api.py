from __future__ import annotations

from typing import Iterator, Dict, Type

from ghoshell.container import Container, Contract
from ghoshell.container import Provider
from ghoshell.contracts import APIRepository, APICaller


class APIRepositoryImpl(APIRepository):
    """
    API 仓库的极简实现.
    """

    def __init__(self):
        self._api_map = {}

    def get_api(self, namespace: str) -> APICaller | None:
        return self._api_map.get(namespace, None)

    def register_api(self, api: APICaller) -> None:
        self._api_map[api.args_type().api_caller] = api

    def foreach_api(self) -> Iterator[APICaller]:
        for name in self._api_map:
            yield self._api_map[name]


class MockAPIRepositoryProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return APIRepository

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return APIRepositoryImpl()
