from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

from ghoshell.ghost.features import IFeaturing
from ghoshell.ghost.intention import Attentions
from ghoshell.ghost.io import Input, Output, Message
from ghoshell.ghost.mindset import Mindset
from ghoshell.ghost.runtime import IRuntime, Task
from ghoshell.ghost.session import Session
from ghoshell.ghost.uml import UML

if TYPE_CHECKING:
    from ghoshell.ghost.mindset import Thought
    from ghoshell.ghost.operation import Operation, OperatorManager


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时的上下文, 努力包含一切核心逻辑与模块
    """

    @property
    @abstractmethod
    def ghost_name(self) -> str:
        """
        机器人的"灵魂"，不同的 Ghost 可能使用同样的灵魂，比如"微软小冰"等
        """
        pass

    @property
    @abstractmethod
    def session(self) -> Session:
        """
        机器人灵魂的"实例",用来隔离 process 与记忆
        """
        pass

    @property
    @abstractmethod
    def input(self) -> Input:
        """
        请求的输入消息, 任何时候都不应该变更.
        """
        pass

    @abstractmethod
    def output(self, *actions: Message) -> None:
        """
        输出各种动作, 实际上输出到 output 里, 给 shell 去处理
        """
        pass

    @abstractmethod
    def async_input(self, _input: Input) -> None:
        """
        ghost 给 ghost 发送信息时使用
        """
        pass

    @abstractmethod
    def reset_input(self, _input: Input) -> None:
        """
        重置上下文的 Input
        """
        pass

    @abstractmethod
    def operate(self, this: "Thought") -> "Operation":
        """
        返回上下文的操作工具
        """
        pass

    @property
    @abstractmethod
    def mind(self) -> Mindset:
        """
        用来获取所有的记忆.
        """
        pass

    @property
    @abstractmethod
    def runtime(self) -> IRuntime:
        """
        与 上下文/进程 相关的存储单元, 用来存储各种数据
        """
        pass

    @property
    @abstractmethod
    def featuring(self) -> IFeaturing:
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
    def gen_output(self) -> Output:
        """
        将所有的输出动作组合起来, 输出为 Output
        所有 act 会积累新的 action 到 output
        它应该是幂等的, 可以多次输出.
        """
        pass

    @abstractmethod
    def reset_output(self, output: Output) -> None:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        上下文级别的缓存机制, 用在内存中.
        """
        pass

    def get(self, key: str) -> Optional[Any]:
        """
        从上下文中获取缓存. 工具机制.
        可惜没有泛型, python 很麻烦的.
        """
        pass

    @abstractmethod
    def new_operator_manager(self) -> "OperatorManager":
        """
        返回一个 OperatorManager
        """
        pass

    def task(self, uml: UML) -> Task:
        """
        从上下文中取出一个 task 对象.
        """
        think = self.mind.fetch(uml.think)
        thought = think.thought(self, uml.args)
        task = self.runtime.get_task(thought.tid)
        if task is None:
            task = Task(
                tid=thought.tid,
                uml=uml,
                pid=self.runtime.process_id(),
            )
            task = thought.to_task(task)
            self.runtime.add_task(task)
        return task

    @abstractmethod
    def destroy(self) -> None:
        """
        上下文运行完成后, 需要考虑 python 的特点, 要主动清理记忆
        """
        pass
