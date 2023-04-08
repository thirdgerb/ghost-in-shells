import uuid
from abc import ABCMeta, abstractmethod
from typing import Set, List, Dict, Optional
from typing import TypeVar

from pydantic import BaseModel

from ghoshell.ghost.exceptions import RuntimeException
from ghoshell.ghost.uml import UML

TASK_STATUS = TypeVar('TASK_STATUS', bound=int)
TASK_LEVEL = TypeVar('TASK_LEVEL', bound=int)


class TaskStatus:
    NEW: TASK_STATUS = 0  # 任务在新建中.

    RUNNING: TASK_STATUS = 1  # 任务中断, 等待响应下一个 Input 事件.
    BLOCKING: TASK_STATUS = 2  # 阻塞, 等待抢占式调度. 一旦任务的优先级低于阻塞中的任务, 就会发生切换事件.
    YIELDING: TASK_STATUS = 3  # 异步任务, 等待下一个异步 Input.
    DEPENDING: TASK_STATUS = 4  # 等待另一个任务的回调.

    FINISHED: TASK_STATUS = 5  # 任务已经完成, 但没有被清除.
    CANCELED: TASK_STATUS = 6  # 任务已经取消
    FAILED: TASK_STATUS = 7  # 任务已经失败

    @classmethod
    def is_waiting_callback(cls, status: TASK_STATUS) -> bool:
        return status in (cls.DEPENDING, cls.YIELDING)

    @classmethod
    def is_able_to_gc(cls, status: TASK_STATUS) -> bool:
        return status in (cls.FINISHED, cls.CANCELED, cls.FAILED)


class TaskLevel:
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
    resolver: str
    stage: str
    is_long_term: bool

    # 当前任务的状态. 只能外部修正.
    status: TASK_STATUS = TaskStatus.NEW

    # 任务的开放程度. 决定了任务执行中是否可以响应别的意图.
    level: TASK_LEVEL = TaskLevel.LEVEL_PUBLIC
    # 当前任务的优先级, 用来抢占式调度.
    # 优先级相同, 则按时间顺序排列.
    priority: float = 0
    # 遗忘的时间戳. 是以秒为单位的 timestamp.
    # < 0 表示不被遗忘的长期记忆.
    # 0 表示不记忆, 完全跟随栈走. 栈被回收就清除. 也可能被一个 LRU 机制淘汰掉.
    # > 1 则是一个 timestamp, 到时间点会遗忘.
    overdue: int = 0
    # forwards 是当前任务的后续状态, 对于 forward 事件生效.
    # 当 forwards 为空时仍然执行 forward 事件, 会转为 finish 事件. 并触发回调.
    forwards: List[str] = []

    # 任务所依赖的 tid
    depending: Optional[str] = None

    attentions: Optional[List[UML]] = None

    args: Dict = {}
    vars: Dict = {}

    @property
    def is_long_term(self) -> bool:
        return self.overdue != 0

    @property
    def is_forgettable(self) -> bool:
        """
        一旦话题切换就可以被遗忘的.
        """
        return TaskStatus.RUNNING == self.status and self.priority < 0

    def add_stages(self, *stages: str) -> None:
        # 将 stages 推入当前的任务中
        stack = list(stages)
        if self.forwards:
            stack.append(*self.forwards)
        self.forwards = stack

    def forward(self) -> bool:
        if len(self.forwards) <= 0:
            return False
        _next = self.forwards[0]
        self.forwards = self.forwards[1:]
        self.depending = None
        if _next == self.stage:
            return self.forward()
        self.stage = _next

    def done(self, status: TASK_STATUS) -> None:
        self.status = status
        self.forwards = []
        self.depending = None

    def reset(self) -> None:
        self.stage = ""
        self.forwards = []
        self.depending = None


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
    """

    # 任务 id
    pid: str

    # session id
    sid: str

    # 每个进程都要有一个 snapshot, 方便进行有状态回溯
    # 高级能力, 暂不急于实现
    # snapshot_id: str

    # snapshot 的回溯.
    # 高级能力, 暂不急于实现
    # backtrace: List[str]

    # 起点任务, 会话的基础. 起点任务可以实现全局的指令和兜底逻辑.
    root: str

    # 当前进行中的任务, 用来响应 Ghost 的 Input
    awaiting: str

    # process 第多少轮次
    # 每接受一次 input 都是一个新的轮次.
    round: int = 0

    parent_id: Optional[str] = None

    # 保存所有的任务指针, 用来做排序等.
    # 避免每个任务读取时的成本.
    tasks: List[Task] = []

    __indexes: Optional[Dict[str, int]] = None

    @property
    def depending(self) -> List[str]:
        """
        等待回调的任务, 依赖另一个任务的完成.
        如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
        """
        return self._get_tid_by_status(TaskStatus.DEPENDING)

    @property
    def root_task(self) -> Task:
        return self.get_task(self.root)

    @property
    def awaiting_task(self) -> Task:
        return self.get_task(self.awaiting)

    @property
    def depended_by_map(self) -> Dict[str, Set[str]]:
        depended_by = {}
        for task in self.tasks:
            if task.status == TaskStatus.DEPENDING:
                depended_task_id = task.depending
                if depended_task_id not in depended_by:
                    depended_by[depended_task_id] = set()
                depended_by[depended_task_id].add(task.tid)
        return depended_by

    @property
    def yielding(self) -> List[str]:
        return self._get_tid_by_status(TaskStatus.YIELDING)

    @property
    def blocking(self) -> List[str]:
        blocking: List[Task] = []
        for task in self.tasks:
            if task.status == TaskStatus.BLOCKING:
                blocking.append(task)
        blocking.sort(key=lambda t: t.priority, reverse=True)
        return [item.tid for item in blocking]

    @property
    def waiting(self) -> List[str]:
        return self._get_tid_by_status(TaskStatus.RUNNING)

    @property
    def finished(self) -> List[str]:
        return self._get_tid_by_status(TaskStatus.FINISHED)

    @property
    def canceled(self) -> List[str]:
        return self._get_tid_by_status(TaskStatus.CANCELED)

    def _get_tid_by_status(self, status: TASK_STATUS) -> List[str]:
        result: List[str] = []
        for task in self.tasks:
            if task.status == status:
                result.append(task.tid)
        return result

    @property
    def is_quiting(self) -> bool:
        return self.round < 0

    @property
    def is_new(self) -> bool:
        return self.round == 0

    def quit(self) -> None:
        self.round = -1

    def get_task(self, tid: str) -> Optional[Task]:
        if self.__indexes is None or len(self.__indexes) == 0:
            self._reset_indexes()
        indexes = self.__indexes
        if tid not in indexes:
            return None
        idx = indexes[tid]
        return self.tasks[idx]

    def store_task(self, *tasks: Task) -> None:
        for p in tasks:
            self._store_single_task(p)
        self._reset_indexes()

    def _store_single_task(self, ptr: Task) -> None:
        """
        当前任务插入到头部.
        每次重拍一下.
        """
        tasks = [ptr]
        storing_id = ptr.tid
        for task in self.tasks:
            if task.tid != storing_id:
                tasks.append(task)
        self.tasks = tasks

    def await_task(self, tid: str):
        self.awaiting = tid

    def reset(self) -> None:
        tasks = [self.root_task]
        self.awaiting = self.root
        self.tasks = tasks
        self._reset_indexes()

    def _reset_indexes(self) -> None:
        indexes = {}
        idx = 0
        for task in self.tasks:
            indexes[task.tid] = idx
            idx += 1
        self.__indexes = indexes

    def gc(self, max_tasks: int = 30) -> List[Task]:
        """
        垃圾回收.
        """
        gc: List[Task] = []
        alive: List[Task] = []
        depended_by = self.depended_by_map
        reversed_tasks = [ptr for ptr in reversed(self.tasks)]
        # 检查基本状态.
        for ptr in reversed_tasks:
            tid = ptr.tid
            if self._is_not_able_to_gc(tid):
                alive.append(ptr)
            if ptr.status == TaskStatus.DEPENDING and ptr.depending not in depended_by:
                # 依赖一个任务, 但任务并不存在.
                gc.append(ptr)
                del depended_by[tid]
            elif tid in depended_by:
                # 如果被依赖中.
                alive.append(ptr)
            elif TaskStatus.is_able_to_gc(ptr.status):
                #  明确可以 gc 的节点.
                gc.append(ptr)
            elif ptr.is_forgettable:
                # 可以被遗忘的任务. 直接从栈里拿掉.
                continue
            else:
                # 正常的节点.
                alive.append(ptr)

        # 如果没有超过栈深, 直接返回.
        if len(alive) < max_tasks:
            self.tasks = alive
            self._reset_indexes()
            return gc

        # 否则用 lru 思路层层 gc
        count = 0
        result = []
        for task in alive:
            count += 1
            tid = task.tid
            if self._is_not_able_to_gc(tid):
                result.append(task)
            elif count > max_tasks:
                continue
            else:
                result.append(task)
            # todo 还需要更多的 gc 逻辑, 这里先这样了.
        self.tasks = result
        self._reset_indexes()

        # 二次清洗.
        # 再检查一次关联性的遗忘.
        more = self.gc(max_tasks)
        gc.append(*more)
        self.__indexes = None
        return gc

    def _is_not_able_to_gc(self, tid: str):
        return tid != self.root and tid != self.awaiting

    @classmethod
    def new_process(cls, sid: str, task: Task, pid: str | None = None, parent_id: str | None = None) -> "Process":
        """
        初始化一个新的
        """
        if pid is None:
            pid = uuid.uuid4()

        return Process(
            sid=sid,
            pid=pid,
            root=task.tid,
            awaiting=task.tid,
            parent_id=parent_id,
            tasks=[task],
        )

    def new_round(self) -> "Process":
        copied = Process(**self.dict())
        copied.round += 1
        return copied


class Runtime(metaclass=ABCMeta):
    """
    用来保存当前运行时的各种状态, 确保异步唤醒时可以读取到.

    Runtime 是一个 Process 级的实现.
    对于一个 Ghost 而言, 可能存在多个 Process.
    """

    @abstractmethod
    def lock_process(self, process_id: str | None = None) -> bool:
        """
        锁一个进程, 避免裂脑.
        由于一个 Session 可能会有一个主进程和多个异步进程
        所以当有明确进程标记时, 可以去命中子进程.
        任何进程处理 input 都是阻塞的.
        """
        pass

    @abstractmethod
    def unlock_process(self, process_id: str | None = None) -> bool:
        pass

    @property
    @abstractmethod
    def session_id(self) -> str:
        """
        返回当前会话的 ID
        通常也是根据会话 ID 来获取 Process.
        """
        pass

    @property
    @abstractmethod
    def current_process_id(self) -> str:
        """
        返回当前会话的 ID
        通常也是根据会话 ID 来获取 Process.
        """
        pass

    def fetch_task(self, tid: str, is_long_term: bool, pid: str | None = None) -> Optional[Task]:
        """
        根据 TaskID 取出一个 Task.
        取不到的话, 说明协议上存在问题.
        """
        process = self.current_process()
        task = process.get_task(tid)
        if task is not None:
            return task
        if is_long_term:
            task = self.fetch_long_term_task(tid)
        if task is not None:
            process.store_task(task)
            return task
        return None

    @abstractmethod
    def fetch_long_term_task(self, tid: str, pid: str | None = None) -> Optional[Task]:
        pass

    def store_task(self, *tasks: Task, pid: str | None = None) -> None:
        """
        添加一个 Task, 在 destroy 的时候才会保存.
        """
        pid = pid if pid else self.current_process_id
        stack = []
        for task in tasks:
            # 保存结束状态的话, 需要清空状态栈
            if TaskStatus.is_able_to_gc(task.status) and len(task.forwards) > 0:
                task.forwards = []
            if task.is_long_term:
                self.store_long_term_task(task)
            stack.append(task)

        process = self.get_process(pid)
        if process is not None:
            process.store_task(*stack)
            self.store_process(process)
        return

    @abstractmethod
    def store_long_term_task(self, task: Task, pid: str | None = None) -> None:
        pass

    @abstractmethod
    def get_process(self, pid: str | None = None) -> Optional[Process]:
        pass

    def current_process(self) -> Process:
        """
        获取当前会话的进程
        """
        process = self.get_process(self.current_process_id)
        if process is None:
            raise RuntimeException(f"current process {self.current_process_id} not found, runtime initialize failed")
        return process

    @abstractmethod
    def rewind(self, pid: str | None = None) -> Process:
        """
        将当前对话的进程和状态全部重置
        None 默认就是当前任务.
        """
        pass

    @abstractmethod
    def store_process(self, process: Process) -> None:
        """
        标记 Process 的状态需要被保存.
        """
        pass

    @abstractmethod
    def finish(self, failed: bool = False) -> None:
        """
        清空持有内容, 需要做的事情:
        1. process 内部的 gc
        2. process 的保存.
        3. 方便 python gc, 删除一些持有的数据.
        """
        pass
