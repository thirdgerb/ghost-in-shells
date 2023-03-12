from __future__ import annotations

import abc
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing import Optional, Dict
    from context import Context

FEAT_KEY = TypeVar('FEAT_KEY', bound=str)


class IFeaturing(metaclass=abc.ABCMeta):
    """
    Ghost 所拥有的所有特征提取能力.
    能够提取出各种和上下文相关的泛化数据. 特征之间可能会有依赖关系
    比如说, 从自然语言中获取 embedding, 用 embedding 匹配到多个意图标识符.
    如果输入的是语音, 则从语音转成了自然语言
    又比如说, 文字输入构成了一个命令行 command -o args 的形式, 可以解析成 "命令特征"
    """

    def feat(self, ctx: Context, feature_id: FEAT_KEY) -> Optional[Dict]:
        pass


class Feature(metaclass=abc.ABCMeta):
    keyword: FEAT_KEY

    def feat(self, ctx: Context) -> None:
        """
        如果希望用类的形式来描述一个特征
        则可以实现 feat 方法, 一个简单的语法糖.
        """
        feat_key = f"__feat_{self.keyword}"
        value = ctx.get(feat_key)
        if value is not None:
            self._assign(value)
            return
        data = ctx.featuring.feat(self.keyword)
        if data is None:
            return
        ctx.set(feat_key, data)
        self._assign(data)

    def _assign(self, data: Dict):
        for key in data:
            if hasattr(self, key):
                setattr(self, key, data[key])
