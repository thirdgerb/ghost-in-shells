from abc import ABCMeta, abstractmethod
from typing import Optional, List, Dict

from ghoshell.ghost import Attentions, Context, Intention


class AttentionDriver(metaclass=ABCMeta):

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        pass

    @abstractmethod
    def register(self, *intentions: Intention) -> None:
        pass

    @abstractmethod
    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        pass


class IAttentions(Attentions):

    def __init__(self, handlers: List[AttentionDriver]):
        self.driver_map: Dict[str, AttentionDriver] = {}
        self.driver_kinds: List[str] = []
        for handler in handlers:
            kind = handler.kind()
            if kind not in self.driver_map:
                self.driver_kinds.append(kind)
            self.driver_map[kind] = handler

    def kinds(self) -> List[str]:
        return self.driver_kinds.copy()

    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        meta_group = {}
        for meta in metas:
            kind = meta.KIND
            if kind not in meta_group:
                meta_group[kind] = []
            meta_group[kind].append(meta)

        for kind in meta_group:
            if kind not in self.driver_map:
                continue
            handler = self.driver_map[kind]
            metas = meta_group[kind]
            matched = handler.match(ctx, *metas)
            if matched is not None:
                return matched
        return None

    def register(self, *metas: Intention) -> None:
        meta_group = {}
        for meta in metas:
            kind = meta.KIND
            if kind not in meta_group:
                meta_group[kind] = []
            meta_group[kind].append(meta)

        for kind in meta_group:
            driver = self.driver_map.get(kind)
            if driver is None:
                continue
            metas = meta_group[kind]
            driver.register(*metas)

    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        for kind in self.driver_kinds:
            driver = self.driver_map[kind]
            matched = driver.wildcard_match(ctx)
            if matched is not None:
                return matched
        return None

    def destroy(self) -> None:
        del self.driver_map
        del self.driver_kinds
