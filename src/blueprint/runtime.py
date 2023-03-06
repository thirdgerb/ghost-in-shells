from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .url import URL
    from typing import Set, List, Tuple, Dict, Optional

TASK_STATUS = TypeVar('TASK_STATUS', bound=int)

TASK_NEW: TASK_STATUS = 0
TASK_AWAIT: TASK_STATUS = 0
TASK_YIELDING: TASK_STATUS = 0
TASK_BLOCKING: TASK_STATUS = 0
TASK_DEPENDING: TASK_STATUS = 0
TASK_FINISHED: TASK_STATUS = 0
TASK_CANCELED: TASK_STATUS = 0


class Task(metaclass=ABCMeta):
    # 全局唯一的 id, 用来保存任务
    _tid: str
    # 任务对应的 resolver
    _url: URL
    # 当前任务的优先级, 用来抢占式调度.
    # 优先级相同, 则按时间顺序排列.
    priority: float

    # 需要保存的状态, 类似栈变量
    data: Dict = {}
    # 当前任务的状态.
    status: TASK_STATUS
    # 当前任务的结果. 如果有结果的话.
    result: Optional[Dict] = None
    # 当前任务的后续状态, 对于 forward 事件生效.
    # forward 为空时会执行 finish 事件. 并出发回调.
    forwards: List[str] = []
    # 任务所依赖的 tid
    depending: Optional[str] = None
    # 任务被依赖的 tid. 任务完成/取消时会将事件传递过去.
    depended: Set[str] = set()
    # 遗忘的时间戳. 是以秒为单位的 timestamp
    overdue: int = -1

    def __init__(self, tid: str, uml: URL, priority: float):
        self._tid = tid
        self._url = uml
        self.priority = priority
        self.status = TASK_NEW

    @property
    def args(self) -> Dict:
        return self._url.args


class Process(metaclass=ABCMeta):
    """
    Ghost 运行中的进程. 进程管理了很多个任务, 这些任务的生命周期都围绕着进程运行.
    """
    root: str
    alive: str
    sleeping: Set[str]
    yielding: Set[str]
    blocking: List[Tuple[float, str]]
    quiting: List[str]
    canceling: List[str]

    finished: List[str]
    canceled: List[str]


class Serializable(metaclass=ABCMeta):

    @abstractmethod
    def marshal(self) -> bytes:
        pass

    @abstractmethod
    def unmarshal(self, serialized: bytes):
        pass


class Serialized(object):
    id: str
    typ: str
    data: bytes


class Runtime(metaclass=ABCMeta):
    """
    用来保存当前运行时的各种状态, 确保异步唤醒时可以读取到.
    """
    pass
