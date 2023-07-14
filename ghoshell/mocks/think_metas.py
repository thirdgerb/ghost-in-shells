from typing import Iterator, Optional, Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.framework.contracts import ThinkMetaStorage
from ghoshell.ghost.mindset import ThinkMeta


class ThinkMetaDriverMock(ThinkMetaStorage):
    """
    测试的 think meta storage.
    deprecated.
    """

    def __init__(self):
        self.__metas = {}
        self.__metas_order = []

    def fetch_meta(self, think_name: str, clone_id: str | None) -> Optional[ThinkMeta]:
        got = self.__metas.get(think_name, None)
        return got

    def iterate_think_metas(self, clone_id: str | None) -> Iterator[ThinkMeta]:
        for name in self.__metas_order:
            yield self.__metas[name]

    def register_meta(self, meta: ThinkMeta, clone_id: str | None) -> None:
        think_name = meta.id
        self.__metas[think_name] = meta
        self.__metas_order.append(think_name)


class ThinkMetaDriverMockProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return ThinkMetaStorage

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return ThinkMetaDriverMock()
