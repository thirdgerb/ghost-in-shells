from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Mindset, Focus, Ghost
from ghoshell.ghost_fmk.contracts import ThinkMetaStorage
from ghoshell.ghost_fmk.mindset import MindsetImpl, LocalFileThinkMetaStorage


class LocalThinkMetaStorageProvider(Provider):

    def __init__(self, relative_runtime_path: str = "think_metas"):
        self.relative_runtime_path = relative_runtime_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return ThinkMetaStorage

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ghost = con.force_fetch(Ghost)
        runtime_path = ghost.runtime_path
        dirname = runtime_path.rstrip("/") + "/" + self.relative_runtime_path.lstrip("/")
        return LocalFileThinkMetaStorage(dirname)


class MindsetProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Mindset

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        driver = con.force_fetch(ThinkMetaStorage)
        focus = con.force_fetch(Focus)
        return MindsetImpl(driver, focus, None)
