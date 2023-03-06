from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing import Dict, Optional, List
    from .mindset import URL

import time

# 输入事件的类型.
EVENT_KIND = TypeVar('EVENT_KIND', bound=str)


class Event(object):
    """
    归一化的消息体.
    ghost 应该定义出自己的消息体系.
    """
    # 消息的类型, 需要显示定义
    kind: EVENT_KIND
    # 消息的数据体, 可以对它进行强类型化
    data: Dict

    def __init__(self, data: Dict):
        self.data = data


class Input(object):
    """
    ghost 的输入
    """
    # 输入的 trace.
    trace: str
    # 传入的事件数据. 应该需要做归一化处理.
    event: Event
    # 环境相关的数据. 协议应该是根据 soul 来定义.
    # shell 应该准确地理解 soul 对协议的定义.
    # 可以放入的信息, 比如: user, shell, origin message 等等.
    env: Dict = {}
    # 如果明确知道命中哪个任务, 可以传 task_id. 否则会用 uuid 生成一个.
    task_id: str = ""
    # 请求相关的场景. 如果 ghost 是初始化, 则用 UML 定位场景.
    scene: Optional[URL] = None
    # 如果是无状态请求, 则任何行为不会变更 ghost 状态.
    stateless: bool = False
    # 异步消息, 回复的消息也应该是异步的.
    is_async: bool = False
    # 时间戳.单位是毫秒
    created_at: float

    def __init__(
            self,
            trace: str,
            event: Event,
            # 以下是可默认字段.
            task_id: str = "",
            uml: URL = None,
            env: Dict = None,
            is_async: bool = False,
            stateless: bool = False,
            created_at: Optional[float] = None,
    ):
        self.trace = trace
        self.event = event
        self.created_at = created_at
        self.uml = uml
        self.task_id = task_id
        if env is None:
            env = {}
        self.env = env
        self.is_async = is_async
        self.stateless = stateless
        if created_at is None:
            created_at = time.time()
        self.created_at = created_at


ACTION_KIND = TypeVar('ACTION_KIND', bound=str)


class Action(object):
    """
    ghost 输出一个动作
    task_id 标记是哪个任务输出的信息
    """
    kind: ACTION_KIND

    def __init__(
            self,
            task_id: str,
            data: Dict,
            created_at: Optional[float] = None,
    ):
        self.task_id: str = task_id
        self.data: Dict = data
        if created_at is None:
            created_at = time.time()
        self.created_at = created_at


class Output(object):
    """
    ghost 的输出.
    """
    # 关联到的输入
    input: Input
    # 运行时拿到的各种动作.
    actions: List[Action] = []
    # 输出的协议, 也需要 ghost 自行定义.
    env: Dict = {}

    def __init__(self, input_: Input):
        """
        实现 output 的初始化
        """
        self.input = input_
