from abc import ABCMeta, abstractmethod
from typing import Set, List, Dict, Optional
from typing import TypeVar

from pydantic import BaseModel

from ghoshell.ghost.uml import UML

TASK_STATUS = TypeVar('TASK_STATUS', bound=int)

TASK_NEW: TASK_STATUS = 0  # 任务在新建中.
TASK_WAIT: TASK_STATUS = 0  # 任务中断, 等待响应下一个 Input 事件.
TASK_YIELDING: TASK_STATUS = 0  # 异步任务, 等待下一个异步 Input.
TASK_BLOCKING: TASK_STATUS = 0  # 阻塞, 等待抢占式调度. 一旦任务的优先级低于阻塞中的任务, 就会发生切换事件.
TASK_DEPENDING: TASK_STATUS = 0  # 等待另一个任务的回调.
TASK_FINISHED: TASK_STATUS = 0  # 任务已经完成, 但没有被清除.
TASK_CANCELED: TASK_STATUS = 0  # 任务已经取消

TASK_LEVEL = TypeVar('TASK_LEVEL', bound=int)

# Private, 封闭域, Process 只能专注于当前任务的 attentions
LEVEL_PRIVATE: TASK_LEVEL = 0
# Protected, 半封闭域, Process 里 task 链上的 task 都可以作为 attentions.
LEVEL_PROTECTED: TASK_LEVEL = 1
# 开放域. 任何全局意图都可以作为 attentions, 反过来说就没有 attentions 了.
LEVEL_PUBLIC: TASK_LEVEL = 2


class Task(BaseModel):
    # 进程内唯一的 id, 最好也是全局唯一 ID
    # 用来作为索引, 在 KV 存储中保存任务体.
    tid: str

    # 任务对应的 resolver, 包含了当前位置
    uml: UML

    # 任务的开放程度. 决定了任务执行中是否可以响应别的意图.
    level: TASK_LEVEL = LEVEL_PUBLIC

    # 进程 id, 用来记录在哪个进程里生成的.
    pid: str = ""

    # 当前任务的状态.
    status: TASK_STATUS

    # 当前任务的优先级, 用来抢占式调度.
    # 优先级相同, 则按时间顺序排列.
    priority: float = 0

    # 当前任务的结果. 如果有结果的话.
    result: Optional[Dict] = None

    # 任务所依赖的 tid
    depending: Optional[str] = None

    # 遗忘的时间戳. 是以秒为单位的 timestamp.
    # < 0 表示长期记忆,
    # 0 表示不记忆, 完全跟随栈走. 栈被回收就清除. 也可能被一个 LRU 机制淘汰掉.
    # > 1 则是一个 timestamp, 到时间点会遗忘.
    overdue: int = 0

    # forwards 是当前任务的后续状态, 对于 forward 事件生效.
    # 当 forwards 为空时仍然执行 forward 事件, 会转为 finish 事件. 并触发回调.
    forwards: List[str] = []

    # 需要保存的状态, 类似栈变量
    data: dict = {}

    # 任务被依赖的 tid. 任务完成/取消时会将事件传递过去.
    depended_by: Set[str] = set()

    attentions: Dict[str, List[Dict]] = {}

    def to_pointer(self) -> "TaskPointer":
        return TaskPointer(
            tid=self.tid,
            status=self.status,
            priority=self.priority,
            level=self.level,
            attentions=self.attentions,
        )
    #
    # @property
    # def is_new(self) -> bool:
    #     return self.status == TASK_NEW
    #
    # @property
    # def is_await(self) -> bool:
    #     return self.status == TASK_AWAIT
    #
    # @property
    # def is_blocking(self) -> bool:
    #     return self.status == TASK_BLOCKING
    #
    # @property
    # def is_depending(self) -> bool:
    #     return self.status == TASK_DEPENDING
    #
    # @property
    # def is_yielding(self) -> bool:
    #     return self.status == TASK_YIELDING
    #
    # @property
    # def is_finished(self) -> bool:
    #     return self.status == TASK_FINISHED
    #
    # @property
    # def is_canceled(self) -> bool:
    #     return self.status == TASK_CANCELED


class TaskPointer(BaseModel):
    """
    相当于任务的指针, 主要提供给 Process 来调度.
    """
    # 任务 id
    tid: str
    # 任务状态
    status: TASK_STATUS
    # 任务的优先级
    priority: float

    level: TASK_LEVEL

    attentions: Dict[str, List[Dict]]


class Process(BaseModel):
    """
    Ghost 实例中运行中的进程.
    每个 Ghost 的实例都会有一个独立的 Session.
    每个 Session 都对应一个独立的 Runtime.
    每个 Runtime 可能运行过 N 个 Process, 但一个时候只会有一个 Process.
    Process 用来标记一个完整的交互流程, 在流程中可能发生了 N 个子任务.
    用操作系统的 Process 来理解就最合适了.

    Process 用来调度运行上下文中的各种 Task.
    不同的 Runtime 算子会使用不同的链来遍历 Process 持有的 Task.

    举例:
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

    # 起点任务, 会话的基础. 起点任务可以实现全局的指令和兜底逻辑.
    root: str

    # 当前进行中的任务, 用来响应 Ghost 的 Input
    current: str

    # 抢占中的任务, 每个会话结束时都会重新排序
    blocking: List[str]

    # 等待回调的任务, 依赖另一个任务的完成.
    # 如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
    depending: Set[str]

    # 等待异步回调的任务.
    # 异步回调是一个 Input 事件
    # 所有输入 Input 会优先匹配 yielding 事件.
    yielding: Set[str]

    # 已经完成的任务. 等待垃圾回收.
    finished: List[str] = []

    # -- 以下是全局属性 -- #

    # 保存所有的任务指针, 用来做排序等.
    # 避免每个任务读取时的成本.
    tasks: List[TaskPointer]


class IRuntime(metaclass=ABCMeta):
    """
    用来保存当前运行时的各种状态, 确保异步唤醒时可以读取到.

    Runtime 是一个 Process 级的实现.
    对于一个 Ghost 而言, 可能存在多个 Process.
    """

    @abstractmethod
    def session_id(self) -> str:
        """
        返回当前会话的 ID
        通常也是根据会话 ID 来获取 Process.
        """
        pass

    @abstractmethod
    def process_id(self) -> str:
        """
        返回当前会话的 ID
        通常也是根据会话 ID 来获取 Process.
        """
        pass

    @abstractmethod
    def get_task(self, tid) -> Optional[Task]:
        """
        根据 TaskID 取出一个 Task.
        取不到的话, 说明协议上存在问题.
        """
        pass

    @abstractmethod
    def add_task(self, task: Task) -> None:
        """
        添加一个 Task, 在 destroy 的时候才会保存.
        """
        pass

    @abstractmethod
    def current_process(self) -> Process:
        """
        获取当前会话的进程
        """
        pass

    @abstractmethod
    def fetch_process(self, pid: str) -> Optional[Process]:
        """
        获取指定的会话进程
        """
        pass

    @abstractmethod
    def quit_process(self) -> None:
        """
        结束当前的 Process. 同时销毁所有运行中的 task.
        """
        pass

    def destroy(self) -> None:
        """
        清空持有内容, 需要做的事情:
        1. process 内部的 gc
        2. process 的保存.
        3. 方便 python gc, 删除一些持有的数据.
        """
        pass
