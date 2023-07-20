from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Type

from ghoshell.ghost.error import MindNotImplementedError
from ghoshell.ghost.mindset.think import Think
from ghoshell.meta import Meta, MetaRepository


class Mindset(MetaRepository[Think], metaclass=ABCMeta):
    """
    定义了 Ghost 拥有的思维方式
    核心是可以通过 UniformReactionLocator 取出 Reaction
    """

    @abstractmethod
    def clone(self, clone_id: str) -> Mindset:
        """
        clone mindset with clone id
        """
        pass

    @classmethod
    def meta_instance_type(cls) -> Type[Think]:
        return Think

    @abstractmethod
    def fetch_meta(self, thinking: str) -> Optional[Meta]:
        """
        获取一个 Thinking的 Meta, 如果存在的话.
        """
        pass

    def force_fetch(self, thinking: str) -> Think:
        """
        随手放一个语法糖方便自己.
        """
        fetched = self.fetch_meta_instance(thinking)
        if fetched is None:
            raise MindNotImplementedError(f"mindset can not find think with name '{thinking}'")
        return fetched

    @abstractmethod
    def destroy(self) -> None:
        pass
