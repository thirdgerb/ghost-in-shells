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

    def register_driver(self, driver: ThinkDriver) -> None:
        # 实现得复杂一些, 可以在这里放各种准入机制.
        key = driver.driver_name()
        self._drivers[key] = driver

    def foreach_think(self) -> Iterator[Think]:
        names = set()
        # 一套遍历策略.
        for meta in self._foreach_local_think_metas():
            if meta.url.resolver in names:
                # 重名的跳过, 不允许遍历. 从而实现继承重写.
                continue
            names.add(meta.url.resolver)
            think = self._wrap_meta(meta)
            if think is not None:
                yield think

        # 遍历所有的子节点.
        for sub in self._sub_mindsets:
            for think in sub.foreach_think():
                name = think.url().resolver
                if name in names:
                    continue
                names.add(name)
                yield think

    @abstractmethod
    def _foreach_local_think_metas(self) -> Iterator[ThinkMeta]:
        pass


class DictMindset(AbstractMindset):
    """
    基于 dict 实现的 mind set.
    显然, 只能作为 demo 使用.
    真实的 mindset 应该要实现分布式配置中心.
    """

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
        self._local_metas[meta.url.resolver] = meta
