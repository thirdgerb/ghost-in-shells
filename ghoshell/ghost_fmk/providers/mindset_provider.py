from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Mindset
from ghoshell.ghost_fmk.mindset import MindsetImpl, ThinkMetaDriver


class MindsetProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Mindset

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        driver = con.force_fetch(ThinkMetaDriver)
        return MindsetImpl(driver, None)
