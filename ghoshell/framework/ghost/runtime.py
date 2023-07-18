from __future__ import annotations

from typing import Dict, List, Optional

from ghoshell.ghost import *
from ghoshell.messages import Tasked
from ghoshell.utils import InstanceCount


class RuntimeImpl(Runtime):

    def __init__(
            self,
            session: Session,
            root_url: URL,
            # 是否是无状态的.
            stateless: bool,
            process_max_tasks: int,
            process_lock_overdue: int,
    ):
        self._stateless = stateless
        self._session: Session = session
        self._session_id: str = session.session_id
        self._process_lock_overdue = process_lock_overdue
        self._process_max_tasks = process_max_tasks

        # init root
        self._root_url = root_url

        # 缓存数据的初始化.
        self._cached_tasks: Dict[str, Dict[str, Task]] = {}
        self._cached_processes: Dict[str, Process | None] = {}
        self._stored_processes: Dict[str, Process | None] = {}
        self._locked: Dict[str, bool] = {}
        self._finished: bool = False
        self._current_process_id = session.current_process_id()

        # 初始化 process.
        self._init_process()

        InstanceCount.add(self.__class__.__name__)

    def _init_process(self):
        """
        初始化 process.
        """
        process = self.get_process(self._current_process_id)
        if not process:
            self._new_process()
        return

    def _new_process(self):
        """
        生成新的 process.
        """
        process = Process.new_process(self._session_id, self._current_process_id, parent_id=None)
        self.store_process(process)

    def get_process(self, pid: str | None = None) -> Process | None:
        """
        获取一个已有的 process.
        """
        pid = pid if pid else self._current_process_id
        if pid not in self._cached_processes:
            self._init_cached_process(pid)
        return self._cached_processes[pid]

    def _init_cached_process(self, pid: str) -> None:
        process_data = self._get_stored_process(pid)
        if process_data is None:
            self._cached_processes[pid] = None
        else:
            process = process_data.new_round()
            self._cached_processes[pid] = process

    def _get_stored_process(self, pid: str) -> Process | None:
        if pid not in self._stored_processes:
            key = self._get_process_key(self._current_process_id)
            process_data = self._session.get(key)
            if process_data is not None:
                self._stored_processes[pid] = Process(**process_data)
            else:
                self._stored_processes[pid] = None
        return self._stored_processes[pid]

    def _get_process_key(self, process_id: str) -> str:
        return f"process:{process_id}"

    def remove_process(self, pid: str) -> None:
        """
        删除一个 process.
        """
        del self._cached_processes[pid]
        del self._stored_processes[pid]
        key = self._get_process_key(self._current_process_id)
        self._session.remove(key)

    def fetch_task(self, tid: str) -> Optional[Task]:
        process = self.current_process()
        # is not instanced
        return process.get_task(tid)

    def store_task(self, *tasks: Task) -> None:
        process = self.current_process()
        process.store_task(*tasks)

    def instance_task(self, ptr: Task) -> Task:
        if ptr.instanced:
            return ptr

        tid = ptr.tid
        if ptr.is_long_term:
            data = self._session.get_task_data(tid)
            if data is not None:
                tasked = Tasked(**data)
                ptr.merge_tasked(tasked)
                ptr.instanced = True
        return ptr

    def lock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._current_process_id
        # 一个 runtime 只锁一次, 避免重复调用方法时死锁.
        if process_id in self._locked:
            return self._locked.get(process_id, False)

        lock_key = self._get_process_locker_key(process_id)
        lock_overdue = self._process_lock_overdue
        locked = self._session.lock(lock_key, lock_overdue)
        self._locked[process_id] = locked
        return locked

    def _get_process_locker_key(self, process_id: str) -> str:
        return f"process_locker:{process_id}"

    def unlock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._current_process_id
        if process_id not in self._locked:
            return False

        # 只有已经锁成功的, 才允许解锁.
        locked = self._locked[process_id]
        if not locked:
            return False

        del self._locked[process_id]
        lock_key = self._get_process_locker_key(process_id)
        return self._session.unlock(lock_key)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def current_process_id(self) -> str:
        return self._current_process_id

    def store_process(self, process: Process) -> None:
        self._cached_processes[process.pid] = process

    def rewind(self, pid: str | None = None) -> None:
        if pid is None:
            pid = self._current_process_id
        self._init_cached_process(pid)

    def _save_all(self) -> None:
        if len(self._cached_processes) == 0:
            return
        for pid in self._cached_processes:
            process = self._cached_processes[pid]
            if process is None:
                continue
            self._save_process(process)

    def _gc_process(self, process: Process) -> List[Task]:
        """
        垃圾回收.
        需要反复进化的复杂逻辑.
        """
        gc: List[Task] = []
        alive: List[Task] = []

        root_id = process.root
        awaiting_id = process.current
        # callbacks = process.callbacks
        max_task = self._process_max_tasks

        # 检查基本状态.
        count = 0
        for ptr in process.tasks:
            tid = ptr.tid
            status = ptr.status
            count += 1
            # 必须要保存的状态.
            if tid == root_id or tid == awaiting_id:
                alive.append(ptr)
            elif ptr.callbacks:
                alive.append(ptr)
            elif TaskStatus.is_sleeping(status):
                alive.append(ptr)
            # 可以被遗忘的状态.
            elif TaskStatus.is_able_to_gc(status):
                gc.append(ptr)
            elif ptr.is_forgettable:
                # 可以被遗忘的任务. 直接从栈里拿掉.
                gc.append(ptr)
            else:
                # 正常的节点.
                alive.append(ptr)

        process.reset_tasks(alive)
        # 重置 process.
        # process.store_task(*reversed(alive))
        return gc

    def _save_process(self, process: Process) -> None:
        # 无状态请求不需要保存状态.
        if self._stateless:
            return

        # 得到需要 gc 的 tasks
        if process.quiting:
            self.remove_process(process.pid)
            return
        gc_tasks = self._gc_process(process)
        # todo: gc 的 tasks 要干什么?
        saving: Dict[str, Tasked] = {}
        for task in process.tasks:
            # 拥有长期记忆的 task 要通过长期记忆来读取.
            if task.is_long_term and task.vars is not None:
                saving[task.tid] = task.to_tasked()
                task.instanced = False
                task.vars = None

        # 删除 process 记忆. 保留长程任务.
        for key in saving:
            tasked = saving[key]
            self._session.set_task_data(tasked.tid, tasked.model_dump(), tasked.overdue)

        process_key = self._get_process_key(process.pid)
        process_data = self._dump_process(process)
        self._session.set(process_key, process_data)

    def _dump_process(self, process: Process) -> Dict:
        """
        定义 process dump 逻辑, 可以在这里做适当的压缩.
        """
        return process.model_dump()

    def finish(self) -> None:
        if self._finished:
            return
        self._save_all()
        self._finished = True

    def destroy(self) -> None:
        del self._session
        del self._cached_processes
        del self._cached_tasks
        del self._stored_processes
        del self._session_id
        del self._current_process_id
        del self._locked
        del self._finished

    def __del__(self):
        InstanceCount.rm(self.__class__.__name__)
