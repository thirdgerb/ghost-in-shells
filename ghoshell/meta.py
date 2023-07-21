from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Dict, Iterator, TypeVar, Generic, Type

from pydantic import BaseModel, Field


# Meta 机制可以理解为在面向对象语言里发明的面向对象机制.
# 面向对象的实现里有  Class 和 Instance 的概念.
# 但这两个概念只对编程语言本身暴露.
# 而对于一个更高级的语言, 一个通过 DSL 定义的系统而言,
# 需要对外暴露的 Class 变成了字符串名字 (meta_kind), 而参数则变成了一个可以用 Schema (json schema) 描述的弱类型数据 (Dict)
# 这样才能让管理域通过 DSL 去驱动 MetaClass 的创建.
# 所以这里的 Meta 机制, 相当于定义了一个面向管理域  DSL 的 class loader.


class Meta(BaseModel):
    """
    数据对象的元数据
    目标是使用这种方式, 在任何地方都能够根据 Meta 数据, 快速实例化一个对象.
    是系统可配置化, 可自解释的核心模块.
    """

    id: str
    kind: str = ""
    config: Dict = Field(default_factory=lambda: {})


class MetaClass(metaclass=ABCMeta):
    """
    一个 Meta 类型的对象.
    意味着它可以通过 Meta 而实例化出来, 也能提供 Meta 数据用于保存.
    """

    @abstractmethod
    def to_meta(self) -> Meta:
        pass


MC = TypeVar('MC', bound=MetaClass)


class MetaDriver(Generic[MC], metaclass=ABCMeta):

    @abstractmethod
    def meta_kind(self) -> str:
        pass

    @abstractmethod
    def meta_config_json_schema(self) -> Dict:
        pass

    @abstractmethod
    def from_meta(self, meta: Meta) -> MC:
        pass


class MetaRepository(Generic[MC], metaclass=ABCMeta):

    @abstractmethod
    def fetch_meta(self, mid: str) -> Meta | None:
        pass

    def fetch_meta_instance(self, mid: str) -> MC | None:
        meta = self.fetch_meta(mid)
        if meta is None:
            return None
        return self.wrap_meta_instance(meta)

    def wrap_meta_instance(self, meta: Meta) -> MC:
        driver = self.get_meta_driver(meta.kind)
        if driver is None:
            raise NotImplementedError(f"meta driver {meta.kind} for {self.__class__.__name__} is not implemented")
        return driver.from_meta(meta)

    @abstractmethod
    def foreach_meta(self) -> Iterator[Meta]:
        pass

    def foreach_meta_instance(self) -> Iterator[MC]:
        """
        需要提供一种机制, 遍历所有的 Think 对象.
        """
        for meta in self.foreach_meta():
            yield self.wrap_meta_instance(meta)

    @abstractmethod
    def register_meta(self, meta: Meta) -> None:
        pass

    @abstractmethod
    def register_meta_driver(self, driver: MetaDriver[MC]) -> None:
        pass

    @abstractmethod
    def get_meta_driver(self, meta_kind: str) -> MetaDriver[MC] | None:
        pass

    def get_meta_json_schema(self, meta_kind: str) -> Dict | None:
        driver = self.get_meta_driver(meta_kind)
        if driver is not None:
            return driver.meta_config_json_schema()
        return None

    @abstractmethod
    def meta_instance_type(self) -> Type[MC]:
        pass


class _MetaManager:

    def __init__(self):
        self._repos: Dict[Type[MetaClass], MetaRepository] = {}

    def get(self, ins_type: Type[MC]) -> MetaRepository[MC]:
        repo = self._repos.get(ins_type, None)
        if repo is None:
            raise NotImplementedError(f"meta repo")
        return repo

    def add(self, repo: MetaRepository[MC]):
        self._repos[repo.meta_instance_type()] = repo


MetaManager = _MetaManager()
