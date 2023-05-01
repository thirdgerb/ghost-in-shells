from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost_fmk.memory import Memory, MemoryImpl


class MemoryProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Memory

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return MemoryImpl()
