from abc import ABCMeta, abstractmethod
from typing import Dict, Any, List, Optional

from ghoshell.ghost import Stage, UML, Thought, Context, Intention, Operator, TASK_LEVEL


class AttentionStage(Stage, metaclass=ABCMeta):
    """
    简写 AS
    能够用意图形式表示的节点.
    专门用来响应一个 Intention
    """

    @abstractmethod
    def intention(self, this: Thought) -> Intention:
        """
        进入当前状态可以提供的各种意图.
        """
        pass

    @abstractmethod
    def attend(self, this: Thought, ctx: Context, args: Dict) -> Operator:
        """
        解决 intention 命中的问题.
        """
        pass


class WaitStage(Stage, metaclass=ABCMeta):
    """
    简写 WS
    等待一个输入事件, 让上下文进入 sleep 状态.
    """

    @abstractmethod
    def wait(self, this: Thought, ctx: Context) -> None:
        """
        进入当前状态的执行逻辑, 比如提问.
        """
        pass

    @abstractmethod
    def level(self) -> TASK_LEVEL:
        """
        返回 PRIVATE, PROTECTED, PUBLIC 三种状态
        - private 则只能路由到当前任务的 attentions
        - protected 则只有当前 process 里的 attentions 可以被识别.
        - public 则全局的各种意图都可以被识别.
        但 root 任务的 attentions 永远都是高优的.
        """
        pass

    @abstractmethod
    def attentions(self, this: Thought, ctx: Context) -> List[UML]:
        """
        从当前状态进入别的状态的连接点.
        可进入的状态, 与自身的开放性有关.

        attentions with intentions
        """
        pass

    def on_preempt(self, this: Thought, ctx: Context) -> Optional[Operator]:
        """
        抢占成功时的动作.
        """
        pass

    @abstractmethod
    def on_fallback(self, this: Thought, ctx: Context):
        """
        用户输入没有命中任何 attentions 时, fallback 到当前状态.
        """
        pass


class InnerStage(Stage, metaclass=ABCMeta):

    @abstractmethod
    def on_start(self, this: Thought, ctx: Context) -> Operator:
        """
        思维链路中的节点.
        没有任何中断能力.
        """
        pass


class DependingStage(Stage, metaclass=ABCMeta):
    """
    DS
    依赖另一个任务的回调.
    """

    @abstractmethod
    def depending(self) -> UML:
        pass

    @abstractmethod
    def on_finished(self, this: Thought, ctx: Context, result: Dict):
        pass

    @abstractmethod
    def on_canceled(self, this: Thought, ctx: Context, reason: Any):
        pass

    @abstractmethod
    def on_failed(self, this: Thought, ctx: Context, reason: Any):
        pass


class YieldingStage(Stage, metaclass=ABCMeta):
    """
    YS
    等待异步回调的节点.
    """

    def on_yield(self, this: Thought, ctx: Context) -> Operator:
        """
        任务在触发 yield 时会做的事情.
        """
        pass

    def yield_to(self) -> UML:
        """
        当前任务让出时, 会启动另一个异步任务.
        异步任务完成后, 会回调到当前任务.
        异步任务会在一个子进程中运行,
        """
        pass

    def on_callback(self, this: Thought, ctx: Context, result: Dict) -> Operator:
        """
        异步任务回调时发生的事情.
        """
        pass
