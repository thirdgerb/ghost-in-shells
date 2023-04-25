import uuid
from abc import ABCMeta, abstractmethod
from typing import List, Dict, Optional, Set

from pydantic import BaseModel, Field

from ghoshell.ghost.exceptions import RuntimeException
from ghoshell.ghost.mindset.focus import Attention
from ghoshell.ghost.url import URL
from ghoshell.messages import Tasked

TASK_STATUS = int
TASK_LEVEL = int


class TaskStatus:
    """
    任务的调度状态. 方便 Runtime 进行多任务调度.
    """

    NEW: TASK_STATUS = 0

    # 任务在运行状态
    RUNNING: TASK_STATUS = 100

    # ---- 以下是中断状态, 等待外部输入 --- #

    # 等待外部输入来继续执行任务.
    # 即便被别的任务打断了, 也仍然会等待用户输入.
    # 期待事件: OnInput
    WAITING: TASK_STATUS = 200  # 等待外部输入来唤醒的任务

    # ---- 以下是调度状态, 等待 Runtime 调度 --- #

    # 任务进入睡眠状态. 等待调度来唤醒. 不会主动响应任何消息.
    # 暂不实现.
    # SLEEPING: TASK_STATUS = 300  # 等待系统调用, 重新激活

    # 等待抢占式调度. 一旦任务的优先级低于阻塞中的任务, 就会发生切换事件.
    PREEMPTING: TASK_STATUS = 300

    # ---- 以下是中断状态, 等待内部回调 --- #

    # 任务正在异步执行中, 等待异步执行结果, 拿到结果后回到正常状态.
    YIELDING: TASK_STATUS = 400

    # 同步任务, 等待另一个或多个同步任务的回调.
    DEPENDING: TASK_STATUS = 500

    # ---- 以下是回收状态 --- #

    # 任务已经完成, 但没有被清除.
    FINISHED: TASK_STATUS = 600

    # 任务取消中
    CANCELING: TASK_STATUS = 700

    # 任务失败中
    FAILING: TASK_STATUS = 800

    # 任务已经彻底取消.
    DEAD: TASK_STATUS = 900

    # @classmethod
    # def is_waiting_callback(cls, status: TASK_STATUS) -> bool:
    #     """
    #     表示任务等待内部的回调.
    #     """
    #     return status in (cls.DEPENDING, cls.YIELDING)
    #
    @classmethod
    def is_final(cls, status: TASK_STATUS) -> bool:
        """
        进入可以被 GC 的状态.
        """
        return status in (cls.FINISHED, cls.DEAD)


class TaskLevel:
    """
    任务 Task 的隔离级别. 目前有三种隔离级别. 对标面向对象的类(class) 中的三种级别.
    """

    # Private, 封闭域, Process 只能专注于当前任务的 focus
    LEVEL_PRIVATE: TASK_LEVEL = 0
    # Protected, 半封闭域, Process 里 task 链上的 task 都可以作为 focus.
    LEVEL_PROTECTED: TASK_LEVEL = 1
    # 开放域. 任何全局意图都可以作为 focus, 反过来说就没有 focus 了.
    LEVEL_PUBLIC: TASK_LEVEL = 2

    @classmethod
    def allow(cls, current_level: int, target_level: int) -> bool:
        if current_level > cls.LEVEL_PUBLIC:
            return False
        if target_level > cls.LEVEL_PUBLIC:
            return False
        return current_level + target_level > cls.LEVEL_PUBLIC


class Task(BaseModel):
    """
    Task 是进程(Process) 中运行的任务单元.
    Task 本身是一个指针, 不包含运行时的数据.
    运行时的数据, 包含上下文记忆, 应该保存在 runtime 中.
    """

    # tid: 任务的唯一 id, 通过 think 来生产.
    # task 分为两种, 一种是短期的, 保存在 process 内部.
    # 另一种是长期的 (long term), 保存在 runtime 中, 可以选择用 clone_id 或者 session_id 等方式做隔离
    # 如果不做隔离, 则所有的 clone 都会共享这个 task.
    # 这会导致运行时的相互覆盖问题, 需要做更复杂的锁来解决隔离.
    tid: str

    # task 自我描述的 resolver, 相当于一个指针.
    url: URL

    # vars: 任务运行中的变量. 保存的时候非指针的信息需要清除掉.
    vars: Dict | None = None

    # 是任务的运行状态. 如果我们把任务理解成一段代码, stage 则指向了代码中的某一行.
    # 值得注意的是, await_stage 只记录任务中断时的位置, 但 resolver 可能有大量的 stages
    # 只有会进入 await 状态的 stage 才会记录到这里.
    await_stage: str = ""

    # status: 当前任务在 runtime 中排列用的状态.
    # 用来让 runtime 调度多个同时存在的 tasks
    status: TASK_STATUS = TaskStatus.RUNNING

    # level: 当前任务的开放程度.
    # 决定了任务执行中, 是否可以被中断. 目前有三种级别.
    level: TASK_LEVEL = TaskLevel.LEVEL_PUBLIC

    # priority: 当前任务的优先级, 用来抢占式调度.
    # 优先级相同, 则按时间顺序排列.
    priority: float = 0

    # overdue: 遗忘的时间戳. 是以秒为单位的 timestamp.
    # overdue < 0 : 表示不被遗忘的长期记忆.
    # overdue 0 : 表示不记忆, 完全跟随栈走. 栈被回收就清除. 也可能被一个 LRU 机制淘汰掉.
    # overdue > 1 : 则应该是一个具体的  unix_timestamp, 到时间点意味着应该被遗忘.
    overdue: int = 0

    # forwards: 是当前任务运行中积压的节点.
    # task 运行 forwards 时应该将 forwards 视作一个 FIFO 栈.
    # 栈的入口为 index == 0, 这样是为了符合人类直觉, 方便查看.
    # 当 forwards 为空时仍然执行 forward 事件, 会转为 finish 事件. 并触发回调.
    forwards: List[str] = Field(default_factory=lambda: [])

    # depending: 如果存在一个任务依赖另一个任务, 这里记录所依赖任务的 tid
    # 被依赖的任务必须要在 process 或者 runtime 里保存, 能够被读取出来.
    callbacks: Set[str] | None = None

    # 考虑增加一个时间戳记录被放入的时间, 但实际上这个时间戳很可能不够敏感?
    # restore_at: float

    attentions: List[Attention] | None = None

    def to_tasked(self) -> Tasked:
        """
        返回出可传输, 可保存的 task 数据.
        """
        return Tasked(
            resolver=self.url.resolver,
            stage=self.url.stage,
            status=self.status,
            args=self.url.args.copy(),
            vars=self.vars,
            tid=self.tid,
        )

    def merge_tasked(self, tasked: Tasked):
        """
        合并一个 tasked 消息.
        """
        # 重置状态.
        self.url.stage = tasked.stage
        self.vars = tasked.vars
        # self.status = tasked.status

    @property
    def is_long_term(self) -> bool:
        """
        表示一个 Task 是否是长期任务.
        长期任务需要 Runtime 用不同的方式来保存.
        """
        return self.overdue != 0

    @property
    def is_forgettable(self) -> bool:
        """
        表示任务本身可以是否可以被遗忘.
        如果是可被遗忘的, 则当任务被中断时, 就会进入静默的垃圾回收过程.
        """
        return TaskStatus.RUNNING == self.status and self.priority < 0

    def insert(self, stages: List[str]) -> None:
        """
        增加新的待运行状态.
        """
        if len(stages) == 0:
            return None
        # 将 stages 推入当前的任务中
        # 注意, 从头开始插入, 符合人类直觉.
        for stage in stages:
            first = self.forwards[0] if len(self.forwards) > 0 else None
            if stage == first:
                continue
            self.forwards.insert(0, stage)
        self.forwards = stages

    def forward(self) -> str | None:
        """
        前进一个状态, 如果为 None 表示栈已经空了.
        """
        if len(self.forwards) == 0:
            return None
        _next = self.forwards[0]
        self.forwards = self.forwards[1:]
        return _next

    def done(self, status: TASK_STATUS, stage: str | None) -> Set[str] | None:
        """
        标记 task 已经结束. 会清空掉状态相关的信息.
        status 应该是回收状态中的一种.
        """
        self.status = status
        self.forwards = []
        if stage is not None:
            self.url.stage = stage
        callbacks = self.callbacks
        self.callbacks = None
        self.attentions = None
        return callbacks

    def add_callback(self, tid: str) -> None:
        if self.callbacks is None:
            self.callbacks = set()
        self.callbacks.add(tid)

    def await_at(self, at_stage: str | None, attentions: List[Attention] | None) -> None:
        """
        等待输入侧的信息.
        """
        self.status = TaskStatus.WAITING
        if at_stage is not None:
            self.url.stage = at_stage
        self.attentions = attentions

    def preempt(self, stage: str | None) -> None:
        """
        进入抢占状态.
        """
        if stage is not None:
            self.url.stage = stage
        self.status = TaskStatus.PREEMPTING
        if stage != self.url.stage:
            self.attentions = None

    #
    # def be_yielding(self, stage: str, yield_to: str) -> None:
    #     """
    #     进入异步等待状态.
    #     """
    #     self.status = TaskStatus.YIELDING
    #     self.await_stage = stage
    #     self.callbacks = yield_to

    def depend(self, stage: str) -> None:
        """
        进入同步等待状态
        """
        self.status = TaskStatus.DEPENDING
        self.url.stage = stage
        self.attentions = None

    def restart(self) -> None:
        """
        强行重置当前任务的状态.
        清空所有多余的信息.
        """
        self.status = TaskStatus.RUNNING
        self.url.stage = ""
        self.forwards = []
        # callbacks 保留
        self.callbacks = self.callbacks
        self.attentions = None


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

    # 任务 process_id
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

    # Runtime 应该可以有多个进程
    # 一个是主进程, 用来响应外部输入
    # 其它的是子进程, 用于执行内部的异步任务
    # 子进程完成之后, 会将 root 任务的结果回调主进程.
    # 如果 parent_id 不为空, 表示自己是异步任务.
    parent_id: Optional[str] = None

    # 保存所有的任务指针, 用来做排序等.
    # 避免每个任务读取时的成本.
    # 注意这个 tasks 是有序的,
    # 所有变更过状态的 task 会保存到数组的头部.
    # 数组的 index == 0 是头部, 符合人类直觉.
    tasks: List[Task] = Field(default_factory=lambda: [])

    # 表示进程是否是退出状态.
    quiting: bool = False

    __indexes: Optional[Dict[str, int]] = None
    __status_list_indexes: Optional[Dict[int, List[str]]] = None

    @classmethod
    def new_process(cls, sid: str, pid: str | None = None, parent_id: str | None = None) -> "Process":
        """
        创建, 初始化一个新的 process.
        """
        if pid is None:
            pid = uuid.uuid4()
        return Process(
            sid=sid,
            pid=pid,
            root="",
            awaiting="",
            parent_id=parent_id,
            tasks=[],
        )

    def new_round(self) -> "Process":
        """
        当前进程运行新的一帧, 每一帧都来自外部信号的输入
        """
        # 考虑强拷贝问题, 没有直接用 base model
        return Process(
            sid=self.sid,
            pid=self.pid,
            root=self.root,
            awaiting=self.awaiting,
            parent_id=self.parent_id,
            rount=self.round + 1,
            tasks=[task.copy() for task in self.tasks],
        )

    @property
    def depending(self) -> List[str]:
        """
        等待回调的任务, 依赖另一个任务的完成.
        如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
        """
        return self._get_tid_by_status(TaskStatus.DEPENDING)

    @property
    def running(self) -> List[str]:
        """
        等待回调的任务, 依赖另一个任务的完成.
        如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
        """
        return self._get_tid_by_status(TaskStatus.RUNNING)

    @property
    def canceling(self) -> List[str]:
        """
        等待回调的任务, 依赖另一个任务的完成.
        如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
        """
        return self._get_tid_by_status(TaskStatus.CANCELING)

    @property
    def failing(self) -> List[str]:
        """
        等待回调的任务, 依赖另一个任务的完成.
        如果上下文命中了一个等待任务, 应该进入到它依赖的对象.
        """
        return self._get_tid_by_status(TaskStatus.FAILING)

    @property
    def is_sub_process(self) -> bool:
        return self.parent_id is not None

    # @property
    # def yielding(self) -> List[str]:
    #     """
    #     取出所有在 yielding 状态中的任务.
    #     """
    #     return self._get_tid_by_status(TaskStatus.YIELDING)

    @property
    def preempting(self) -> List[str]:
        """
        取出所有在 blocking 状态中的任务.
        同时对这些任务进行 priority 优先级排序.
        二级顺序应该是运行时数据.
        """
        preempting: List[Task] = []
        for task in self.tasks:
            if task.status == TaskStatus.PREEMPTING:
                preempting.append(task)
        preempting.sort(key=lambda t: t.priority, reverse=True)
        return [item.tid for item in preempting]

    @property
    def waiting(self) -> List[str]:
        """
        取出所有的运行中任务.
        要排除掉 await 和 root
        """
        arr = self._get_tid_by_status(TaskStatus.WAITING)
        result = []
        # todo, 这样写感觉运行效率比较低, 内存开销增加. 不过问题不大.
        for tid in arr:
            if tid != self.root and tid != self.awaiting:
                result.append(tid)
        return result

    @property
    def finished(self) -> List[str]:
        """
        取出所有已经正常完成的任务.
        """
        return self._get_tid_by_status(TaskStatus.FINISHED)

    def _get_tid_by_status(self, status: TASK_STATUS) -> List[str]:
        if self.__status_list_indexes is None:
            status_indexes = {}
            for task in self.tasks:
                status = task.status
                if status not in status_indexes:
                    status_indexes[status] = []
                status_indexes[status].append(task.tid)
            self.__status_list_indexes = status_indexes

        return self.__status_list_indexes.get(status, [])

    @property
    def is_new(self) -> bool:
        """
        标记是一个从头开始的新进程.
        新进程在接受外部输入信号时, root task 应该要先运行 start 流程, 对整体状态进行初始化.
        """
        return self.round == 0

    def add_round(self) -> None:
        self.round = self.round + 1

    def get_task(self, tid: str) -> Optional[Task]:
        """
        取出来一个任务的指针.
        """
        if self.__indexes is None or len(self.__indexes) == 0:
            self.__reset_indexes()
        indexes = self.__indexes
        if tid not in indexes:
            return None
        idx = indexes[tid]
        return self.tasks[idx]

    def store_task(self, *tasks: Task) -> None:
        """
        将任务记录到 Process 中.
        每次要重置索引.
        """
        for task in tasks:
            if not self.root:
                self.root = task.tid
            self._store_single_task(task)
        self.__clear()

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

    def await_at(self, tid: str):
        """
        将进程 await at 到一个任务上.
        """
        self.awaiting = tid

    def reset(self) -> None:
        """
        将进程重置到根任务上.
        """
        root = self.get_task(self.root)
        root.restart()
        self.awaiting = self.root
        self.tasks = [root]
        self.__clear()

    def __clear(self) -> None:
        self.__indexes = None
        self.__status_list_indexes = None

    def fallback(self) -> Task | None:
        canceling = self.canceling
        if len(canceling) > 0:
            return self.get_task(canceling[0])
        failing = self.failing
        if len(failing) > 0:
            return self.get_task(failing[0])

        # running = self.running
        # if len(running) > 0:
        #     tid = running[0]
        #     # running 的任务执行 forward
        #     return self.get_task(tid)

        preempting = self.preempting
        if len(preempting) > 0:
            tid = preempting[0]
            return self.get_task(tid)

        waiting = self.waiting
        if len(waiting) > 0:
            tid = waiting[0]
            return self.get_task(tid)
        return None

    def __reset_indexes(self) -> None:
        indexes = {}
        idx = 0
        for task in self.tasks:
            indexes[task.tid] = idx
            idx += 1
        self.__indexes = indexes

    # def gc(self, max_tasks: int = 30) -> List[Task]:
    #     """
    #     垃圾回收.
    #     需要反复进化的复杂逻辑.
    #     """
    #     gc: List[Task] = []
    #     alive: List[Task] = []
    #     depended_by = self.depended_by_map
    #     reversed_tasks = [ptr for ptr in reversed(self.tasks)]
    #     # 检查基本状态.
    #     for ptr in reversed_tasks:
    #         tid = ptr.tid
    #         if self._is_not_able_to_gc(tid):
    #             alive.append(ptr)
    #         if ptr.status == TaskStatus.DEPENDING and ptr.depending not in depended_by:
    #             # 依赖一个任务, 但任务并不存在.
    #             gc.append(ptr)
    #             del depended_by[tid]
    #         elif tid in depended_by:
    #             # 如果被依赖中.
    #             alive.append(ptr)
    #         elif TaskStatus.is_able_to_gc(ptr.status):
    #             #  明确可以 gc 的节点.
    #             gc.append(ptr)
    #         elif ptr.is_forgettable:
    #             # 可以被遗忘的任务. 直接从栈里拿掉.
    #             continue
    #         else:
    #             # 正常的节点.
    #             alive.append(ptr)
    #
    #     # 如果没有超过栈深, 直接返回.
    #     if len(alive) < max_tasks:
    #         self.tasks = alive
    #         self._reset_indexes()
    #         return gc
    #
    #     # 否则用 lru 思路层层 gc
    #     count = 0
    #     result = []
    #     for task in alive:
    #         count += 1
    #         tid = task.tid
    #         if self._is_not_able_to_gc(tid):
    #             result.append(task)
    #         elif count > max_tasks:
    #             continue
    #         else:
    #             result.append(task)
    #         # todo 还需要更多的 gc 逻辑, 这里先这样了.
    #     self.tasks = result
    #     self._reset_indexes()
    #
    #     # 二次清洗.
    #     # 再检查一次关联性的遗忘.
    #     more = self.gc(max_tasks)
    #     gc.append(*more)
    #     self.__indexes = None
    #     return gc
    #
    # def _is_not_able_to_gc(self, tid: str):
    #     return tid != self.root and tid != self.awaiting


class Runtime(metaclass=ABCMeta):
    """
    用来保存当前运行时的各种状态, 确保异步唤醒时可以读取到.

    Runtime 是一个 Process 级的实现.
    对于一个 Ghost 而言, 可能存在多个 Process.
    """

    @property
    @abstractmethod
    def session_id(self) -> str:
        """
        返回当前会话的 ID
        通常也是根据会话 ID 来获取 Process.
        """
        pass

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

    @abstractmethod
    def get_process(self, pid: str | None = None) -> Optional[Process]:
        """
        取出一个 process
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

    def current_process(self) -> Process:
        """
        获取当前会话的进程
        """
        process = self.get_process(self.current_process_id)
        if process is None:
            raise RuntimeException(f"current process {self.current_process_id} not found, runtime initialize failed")
        return process

    @abstractmethod
    def gc_process(self, process: Process) -> None:
        """
        提供一个算法, 用来将 process 里的数据进行精简
        这个方法通常在 finish 方法中被调用.
        """
        pass

    @abstractmethod
    def fetch_task(self, tid: str) -> Optional[Task]:
        """
        根据 TaskID 取出一个 Task.
        Task 本身是一个任务的指针, tid 自己就包含了隔离级别
        如果不能正确取出的话, 则应该用初始化的 task 去获取信息.
        """
        pass

    @abstractmethod
    def store_task(self, *tasks: Task) -> None:
        """
        添加一个 Task, 通常在 finish 的时候才会保存.
        """
        pass

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
    def finish(self) -> None:
        """
        清空持有内容, 需要做的事情:
        1. process 内部的 gc
        2. process 的保存.
        3. 方便 python gc, 删除一些持有的数据.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        方便垃圾回收
        """
        pass
