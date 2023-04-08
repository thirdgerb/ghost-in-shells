from abc import ABCMeta, abstractmethod
from typing import Optional, Iterator, List, Dict

from ghoshell.ghost import Mindset, Think
from ghoshell.ghost.mindset import ThinkMeta, ThinkDriver


class AbstractMindset(Mindset, metaclass=ABCMeta):

    def __init__(self):
        self._sub_mindsets: List[Mindset] = []
        self._drivers: Dict[str, ThinkDriver] = {}

    def fetch(self, thinking: str) -> Optional[Think]:
        meta = self._fetch_local_meta(thinking)
        if meta is not None:
            think = self._wrap_meta(meta)
            if think is not None:
                return think
        for sub in self._sub_mindsets:
            think = sub.fetch(thinking)
            if think is not None:
                return think
        return None

    def _wrap_meta(self, meta: ThinkMeta) -> Think | None:
        driver = self._drivers.get(meta.driver, None)
        if driver is not None:
            return driver.from_meta(meta)
        return None

    @abstractmethod
    def _fetch_local_meta(self, thinking: str) -> Optional[ThinkMeta]:
        pass

    def fetch_meta(self, thinking: str) -> Optional[ThinkMeta]:
        meta = self._fetch_local_meta(thinking)
        if meta is not None:
            return meta
        for sub in self._sub_mindsets:
            meta = sub.fetch_meta(thinking)
            if meta is not None:
                return meta
        return None

    def register_sub_mindset(self, mindset: Mindset) -> None:
        self._sub_mindsets.append(mindset)

    def register_driver(self, key: str, driver: ThinkDriver) -> None:
        self._drivers[key] = driver

    def foreach_think(self) -> Iterator[Think]:
        for meta in self._foreach_local_think_metas():
            think = self._wrap_meta(meta)
            if think is not None:
                yield think

        for sub in self._sub_mindsets:
            for think in sub.foreach_think():
                yield think

    @abstractmethod
    def _foreach_local_think_metas(self) -> Iterator[ThinkMeta]:
        pass


class LocalMindset(AbstractMindset):

    def __init__(self):
        self._local_metas: Dict[str, ThinkMeta] = {}
        super().__init__()

    def _fetch_local_meta(self, thinking: str) -> Optional[ThinkMeta]:
        return self._local_metas.get(thinking, None)

    def _foreach_local_think_metas(self) -> Iterator[ThinkMeta]:
        for key in self._local_metas:
            meta = self._local_metas[key]
            yield meta

    def register_meta(self, meta: ThinkMeta) -> None:
        self._local_metas[meta.uml.think] = meta
