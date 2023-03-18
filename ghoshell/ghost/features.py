from __future__ import annotations

import abc
from typing import Optional, Dict
from typing import TypeVar

from context import IContext

FEAT_KEY = TypeVar('FEAT_KEY', bound=str)


class IFeaturing(metaclass=abc.ABCMeta):
    """
    Ghost 所拥有的所有特征提取能力.
    能够提取出各种和 `当前上下文` 相关的泛化数据. 特征之间可能会有依赖关系
    比如说, 从自然语言中获取 embedding, 用 embedding 匹配到多个意图标识符. 但如果输入的是语音, 可能需要从语音先转成文字.
    又比如说, 文字输入构成了一个命令行 command -options *args 的形式, 可以解析成 "命令特征"

    特征工程有很多种实现方式, 这个抽象就尽可能简单了.
    """

    def feat(self, ctx: IContext, feature_id: FEAT_KEY) -> Optional[Dict]:
        pass


class Feature(metaclass=abc.ABCMeta):
    """
    特征的语法糖, 用来从上下文中获取强类型约束的特征数据.
    python 弱类型有弱类型的好处, 坏处就是写代码没提示不会写.
    """
    keyword: FEAT_KEY

    def feat(self, ctx: IContext) -> bool:
        """
        如果希望用类的形式来描述一个特征
        则可以实现 feat 方法, 一个简单的语法糖.
        """
        feat_key = f"__feat_{self.keyword}"
        value = ctx.get(feat_key)
        if value is not None:
            self._assign(value)
            return True
        data = ctx.featuring.feat(self.keyword)
        if data is None:
            return False
        ctx.set(feat_key, data)
        self._assign(data)
        return True

    @abc.abstractmethod
    def _assign(self, data: Dict) -> "Feature":
        """
        用来分配数据. 通常就从 dict 展开好了.
        这里应该是后期静态绑定, 但暂时还不会
        """
        pass
