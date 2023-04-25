from abc import ABCMeta, abstractmethod
from typing import Optional, List, Dict

from ghoshell.ghost import Focus, Context, Intention


class AttentionHandler(metaclass=ABCMeta):

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        pass

    @abstractmethod
    def register_global_intentions(self, *intentions: Intention) -> None:
        pass

    @abstractmethod
    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        pass


class AttentionImpl(Focus):
    """
    一个最简单的实现.
    """

    def __init__(self, *drivers: AttentionHandler):
        self.driver_map: Dict[str, AttentionHandler] = {}
        # 保证有序.
        self.driver_kinds: List[str] = []
        for driver in drivers:
            self.register_driver(driver)

    def clone(self) -> "Focus":
        return self

    def kinds(self) -> List[str]:
        return self.driver_kinds.copy()

    def register_driver(self, driver: AttentionHandler) -> None:
        kind = driver.kind()
        if kind not in self.driver_map:
            self.driver_kinds.append(kind)
        # 替换已经有的 driver
        self.driver_map[kind] = driver

    def match(self, ctx: Context, kind: str, *metas: Intention) -> Optional[Intention]:
        """
        按类型匹配.
        """
        driver = self.driver_map.get(kind, None)
        if driver is None:
            return None
        arr = []
        for meta in metas:
            if meta.kind != kind:
                continue
            arr.append(meta)
        if len(arr) == 0:
            return None
        return driver.match(ctx, *metas)

    def register_global_intentions(self, *metas: Intention) -> None:
        meta_group = {}
        for meta in metas:
            kind = meta.kind
            if kind not in meta_group:
                meta_group[kind] = []
            meta_group[kind].append(meta)

        for kind in meta_group:
            driver = self.driver_map.get(kind)
            if driver is None:
                continue
            metas = meta_group[kind]
            driver.register_global_intentions(*metas)

    def global_match(self, ctx: Context) -> Optional[Intention]:
        for kind in self.driver_kinds:
            driver = self.driver_map[kind]
            matched = driver.wildcard_match(ctx)
            if matched is not None:
                return matched
        return None

    def destroy(self) -> None:
        del self.driver_map
        del self.driver_kinds
