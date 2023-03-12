from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional
from typing import TypeVar

from dataclasses_json import dataclass_json

from ghoshell.ghost.uml import UML

TASK_STATUS = TypeVar('TASK_STATUS', bound=int)

TASK_NEW: TASK_STATUS = 0  # 新建
TASK_AWAIT: TASK_STATUS = 0  # 中断, 等待
TASK_YIELDING: TASK_STATUS = 0  # 异步等待
TASK_BLOCKING: TASK_STATUS = 0  # 阻塞, 等待调度
TASK_DEPENDING: TASK_STATUS = 0  # 依赖当前任务完成
TASK_FINISHED: TASK_STATUS = 0  # 任务已经完成, 状态还没清除
TASK_CANCELED: TASK_STATUS = 0  # 任务已经取消


@dataclass_json
@dataclass
class Task:
    pid: str
    # 进程内唯一的 id, 用来保存任务
    tid: str
    # 任务对应的 resolver
    url: UML
    # 当前任务的优先级, 用来抢占式调度.
    # 优先级相同, 则按时间顺序排列.
    priority: float

    # 当前任务的状态.
    status: TASK_STATUS
    # 当前任务的结果. 如果有结果的话.
    result: Optional[Dict] = None

    # 任务所依赖的 tid
    depending: Optional[str] = None

    # 遗忘的时间戳. 是以秒为单位的 timestamp
    overdue: int = -1
    # 当前任务的后续状态, 对于 forward 事件生效.

    # forward 为空时会执行 finish 事件. 并出发回调.
    forwards: List[str] = field(default_factory=lambda: [])

    # 需要保存的状态, 类似栈变量
    data: dict = field(default_factory=lambda: {})

    # 任务被依赖的 tid. 任务完成/取消时会将事件传递过去.
    depended: Set[str] = field(default_factory=lambda: set())


class TaskPointer(object):
    tid: str
    status: TASK_STATUS
    priority: float


class Process(metaclass=ABCMeta):
    """
    Ghost 运行中的进程. 进程管理了很多个任务, 这些任务的生命周期都围绕着进程运行.

    - receive 链: root -> awaits -> blocking -> sleeping
    - fallback 链: awaits -> sleeping
    """
    # 任务 id
    pid: str

    # 每个进程都要有一个 snapshot, 方便进行有状态回溯
    # 高级能力, 暂不急于实现
    # snapshot_id: str

    # snapshot 的回溯.
    # 高级能力, 暂不急于实现
    # backtrace: List[str]

    # 起点任务, 会话的基础.
    root: str
    # 等待回调的任务, 由它开始建立 fallback 链
    awaits: str
    # 抢占中的任务, 每个会话结束时都会重新排序
    blocking: List[str]
    sleeping: Set[str]
    yielding: Set[str]

    canceling: List[str]
    finished: List[str]
    tasks: List[TaskPointer]


class IRuntime(metaclass=ABCMeta):
    """
    用来保存当前运行时的各种状态, 确保异步唤醒时可以读取到.
    """

    @abstractmethod
    def current_task(self) -> Task:
        pass

    @abstractmethod
    def get_task(self, tid) -> Optional[Task]:
        """
        """
        pass

    @abstractmethod
    def process(self) -> Process:
        """
        获取当前会话的进程
        """
        pass

    @abstractmethod
    def process_gc(self) -> None:
        """
        清除掉过期的任务
        节省 task 相关的栈空间
        """
        pass

    def destroy(self) -> None:
        """
        清空持有内容, 方便 python 的 gc
        """
        pass
