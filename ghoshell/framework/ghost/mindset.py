import hashlib
import os
from typing import Optional, Iterator, List, Dict

import yaml

from ghoshell.framework.contracts.think_meta_storage import ThinkMetaStorage  # ThinkMetaDriverProvider
from ghoshell.ghost import Mindset, Think, Focus
from ghoshell.ghost.mindset import ThinkMeta, ThinkDriver


class MindsetImpl(Mindset):

    def __init__(self, driver: ThinkMetaStorage, focus: Focus, clone_id: str | None):
        self._think_metas_driver = driver  # 这个 driver 专门用于保存 ThinkMeta. 用于动态存储.
        self._clone_id = clone_id
        self._sub_mindsets: List[Mindset] = []
        self._think_drivers: Dict[str, ThinkDriver] = {}
        self._focus = focus

    @property
    def focus(self) -> Focus:
        return self._focus

    def clone(self, clone_id: str) -> Mindset:
        mindset = MindsetImpl(self._think_metas_driver, self._focus, clone_id)
        mindset.register_sub_mindset(self)
        return mindset

    def fetch(self, thinking: str) -> Optional[Think]:
        meta = self.fetch_meta(thinking)
        if meta is not None:
            return self._wrap_meta(meta)
        return None

    def _wrap_meta(self, meta: ThinkMeta) -> Think | None:
        driver = self.get_driver(meta.kind)
        if driver is None:
            return None
        return driver.from_meta(meta)

    def fetch_meta(self, thinking: str) -> Optional[ThinkMeta]:
        meta = self._think_metas_driver.fetch_meta(thinking, self._clone_id)
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
        self._think_drivers[key] = driver

    def get_driver(self, driver_name: str) -> ThinkDriver | None:
        if driver_name in self._think_drivers:
            return self._think_drivers[driver_name]
        for sub in self._sub_mindsets:
            driver = sub.get_driver(driver_name)
            if driver is not None:
                self._think_drivers[driver_name] = driver
                return driver
        return None

    def foreach_think(self) -> Iterator[Think]:
        names = set()
        # 一套遍历策略.
        for meta in self._think_metas_driver.iterate_think_metas(self._clone_id):
            if meta.id in names:
                # 重名的跳过, 不允许遍历. 从而实现继承重写.
                continue
            names.add(meta.id)
            think = self._wrap_meta(meta)
            if think is not None:
                yield think

        # 遍历所有的子节点.
        for sub in self._sub_mindsets:
            for think in sub.foreach_think():
                name = think.url().think
                if name in names:
                    continue
                names.add(name)
                yield think

    def register_meta(self, meta: ThinkMeta) -> None:
        """
        注册一个 thinking
        当然, Mindset 可以有自己的实现, 从某个配置体系中获取.
        或者合并多个 Mindset.
        """
        self._think_metas_driver.register_meta(meta, self._clone_id)

    def destroy(self) -> None:
        if self._clone_id is not None:
            del self._clone_id
            del self._think_metas_driver
            del self._think_drivers
            del self._sub_mindsets


class LocalFileThinkMetaStorage(ThinkMetaStorage):
    """
    基于本地文件的 think meta storage
    """

    def __init__(self, dirname: str):
        self.dirname = dirname
        self._cached_metas: Dict[str, ThinkMeta | None] = {}
        self._cached_filename_2_think: Dict[str, str] = {}

    def fetch_meta(self, think_name: str, clone_id: str | None) -> Optional[ThinkMeta]:
        if think_name in self._cached_metas:
            return self._cached_metas[think_name]
        filename = self._make_filename(think_name)
        if not os.path.exists(filename):
            self._cached_metas[think_name] = None
            return None
        return self._get_meta_by_filename(filename)

    def _get_meta_by_filename(self, filename) -> ThinkMeta:
        if filename in self._cached_filename_2_think:
            think_name = self._cached_filename_2_think[filename]
            return self._cached_metas.get(think_name)
        with open(filename) as f:
            data = yaml.safe_load(f)
            meta = ThinkMeta(**data)
            self._cached_metas[meta.id] = meta
            self._cached_filename_2_think[filename] = meta.id
            return meta

    def _make_filename(self, think_name: str):
        basename = hashlib.md5(think_name.encode()).hexdigest()
        return self.dirname.rstrip("/") + "/" + basename + ".yaml"

    def iterate_think_metas(self, clone_id: str | None) -> Iterator[ThinkMeta]:
        for root, ds, fs in os.walk(self.dirname):
            for fullname in fs:
                filename = self.dirname.rstrip("/") + "/" + fullname
                yield self._get_meta_by_filename(filename)

    def register_meta(self, meta: ThinkMeta, clone_id: str | None) -> None:
        self._cached_metas[meta.id] = meta
        filename = self._make_filename(meta.id)
        with open(filename, 'w') as f:
            yaml.safe_dump(meta.model_dump(), f, allow_unicode=True)
