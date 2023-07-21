from __future__ import annotations

import hashlib
import os
from typing import Optional, Iterator, Dict

import yaml

from ghoshell.framework.contracts import ThinkMetaStorage  # ThinkMetaDriverProvider
from ghoshell.ghost import Mindset, ThinkDriver
from ghoshell.meta import Meta


class MindsetImpl(Mindset):

    def __init__(self, storage: ThinkMetaStorage, clone_id: str | None):
        self._think_metas_storage = storage.clone(clone_id)  # 这个 driver 专门用于保存 ThinkMeta. 用于动态存储.
        self._think_meta_drivers = {}
        self._clone_id = clone_id

    def clone(self, clone_id: str) -> Mindset:
        mindset = MindsetImpl(self._think_metas_storage, clone_id)
        mindset._think_meta_drivers = self._think_meta_drivers.copy()
        return mindset

    def fetch_meta(self, thinking: str) -> Optional[Meta]:
        meta = self._think_metas_storage.fetch_meta(thinking, self._clone_id)
        if meta is not None:
            return meta
        return None

    def register_meta_driver(self, driver: ThinkDriver) -> None:
        self._think_meta_drivers[driver.meta_kind()] = driver
        for meta in driver.preload_metas():
            self.register_meta(meta)

    def get_meta_driver(self, meta_kind: str) -> ThinkDriver | None:
        return self._think_meta_drivers.get(meta_kind, None)

    def foreach_meta(self) -> Iterator[Meta]:
        for meta in self._think_metas_storage.iterate_think_metas():
            yield meta

    def register_meta(self, meta: Meta) -> None:
        """
        注册一个 thinking
        当然, Mindset 可以有自己的实现, 从某个配置体系中获取.
        或者合并多个 Mindset.
        """
        self._think_metas_storage.register_meta(meta, self._clone_id)

    def destroy(self) -> None:
        if self._clone_id is not None:
            del self._clone_id
            del self._think_metas_storage
            del self._think_meta_drivers


class LocalFileThinkMetaStorage(ThinkMetaStorage):
    """
    基于本地文件的 think meta storage
    """

    def __init__(self, dirname: str):
        self.dirname = dirname
        self._cached_metas: Dict[str, Meta | None] = {}
        self._cached_filename_2_think: Dict[str, str] = {}

    def fetch_meta(self, think_name: str, clone_id: str | None) -> Optional[Meta]:
        if think_name in self._cached_metas:
            return self._cached_metas[think_name]
        filename = self._make_filename(think_name)
        if not os.path.exists(filename):
            self._cached_metas[think_name] = None
            return None
        return self._get_meta_by_filename(filename)

    def _get_meta_by_filename(self, filename) -> Meta:
        if filename in self._cached_filename_2_think:
            think_name = self._cached_filename_2_think[filename]
            return self._cached_metas.get(think_name)
        with open(filename) as f:
            data = yaml.safe_load(f)
            meta = Meta(**data)
            self._cached_metas[meta.id] = meta
            self._cached_filename_2_think[filename] = meta.id
            return meta

    def _make_filename(self, think_name: str):
        basename = hashlib.md5(think_name.encode()).hexdigest()
        return self.dirname.rstrip("/") + "/" + basename + ".yaml"

    def clone(self, clone_id: str | None) -> ThinkMetaStorage:
        return self

    def iterate_think_metas(self) -> Iterator[Meta]:
        for root, ds, fs in os.walk(self.dirname):
            for fullname in fs:
                filename = self.dirname.rstrip("/") + "/" + fullname
                yield self._get_meta_by_filename(filename)

    def register_meta(self, meta: Meta, clone_id: str | None) -> None:
        self._cached_metas[meta.id] = meta
        filename = self._make_filename(meta.id)
        with open(filename, 'w') as f:
            yaml.safe_dump(meta.model_dump(), f, allow_unicode=True)
