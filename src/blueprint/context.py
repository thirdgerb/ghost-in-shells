from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, Any
    from .io import Input, Output, Action
    from .mindset import Mindset
    from .runtime import Runtime
    from .intention import Attentions
    from features import Featuring


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时的上下文, 努力包含一切核心逻辑与模块
    """

    @property
    @abstractmethod
    def soul(self) -> str:
        """
        机器人的"灵魂"，不同的 Ghost 可能使用同样的灵魂，比如"微软小冰"等
        """
        pass

    @property
    @abstractmethod
    def ghost(self) -> str:
        """
        机器人灵魂的"实例",用来隔离 process 与记忆
        """
        pass

    @property
    @abstractmethod
    def input(self) -> Input:
        """
        请求的输入消息
        """
        pass

    @property
    @abstractmethod
    def mind(self) -> Mindset:
        pass

    @property
    @abstractmethod
    def runtime(self) -> Runtime:
        """
        与 上下文/进程 相关的存储单元, 用来存储各种数据
        """
        pass

    @property
    @abstractmethod
    def featuring(self) -> Featuring:
        """
        从上下文中获取特征.
        特征是和上下文相关的任何信息.
        通常不包含记忆.
        """
        pass

    @property
    @abstractmethod
    def attentions(self) -> Attentions:
        """
        机器人状态机当前保留的工程化注意力机制
        与算法不同, 注意的可能是命令行, API, 事件等复杂信息.
        """
        pass

    @abstractmethod
    def act(self, *actions: Action) -> None:
        """
        输出各种动作, 实际上输出到 output 里, 给 shell 去处理
        """
        pass

    @abstractmethod
    def output(self) -> Output:
        """
        将所有的输出动作组合起来, 输出为 Output
        所有 act 会积累新的 action 到 output
        它应该是幂等的, 可以多次输出.
        """
        pass

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        用 context 来获取请求级的变量数据.
        key 应该是 JSON Pointer 等标准化的路径
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        用 context 来临时保存请求级的变量数据.
        key 应该是 JSON Pointer 等标准化的路径
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        上下文运行完成后, 需要考虑 python 的特点, 要主动清理记忆
        """
        pass
