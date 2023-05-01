from abc import ABCMeta, abstractmethod
from typing import Dict, Any

from pydantic import BaseModel, Field

from ghoshell.container import Container


class Meta(BaseModel):
    """
    对于 Python 实例可配置的通用方案.
    """
    id: str

    # meta 的类型.
    kind: str

    # meta 的配置内容, 是一个 dict 表示的数据.
    config: Dict = Field(default_factory=dict)


class MetaClass(metaclass=ABCMeta):
    """
    可以生成 meta 数据的类.
    也意味着可以通过 meta 数据进行实例化.
    """

    @abstractmethod
    def to_meta(self) -> Meta:
        pass


class MetaProvider(metaclass=ABCMeta):
    """
    用来将 meta 生成为 MetaClass
    失败应该返回 Exception.
    """

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def instance(self, con: Container, meta: Meta) -> MetaClass:
        pass


class MetaContainer:
    """
    Meta 数据的容器.
    """

    def __init__(self):
        self._providers: Dict[str, MetaProvider] = {}

    def register(self, provider: MetaProvider) -> None:
        self._providers[provider.kind()] = provider

    def instance(self, con: Container, meta: Meta) -> Any | None:
        kind = meta.kind
        if kind not in self._providers:
            return None
        provider = self._providers[kind]
        return provider.instance(con, meta)
