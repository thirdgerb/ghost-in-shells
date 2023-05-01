from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Focus
from ghoshell.ghost_fmk.focus import FocusImpl


class FocusProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Focus

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return FocusImpl()
