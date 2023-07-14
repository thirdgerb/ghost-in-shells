from __future__ import annotations

import json
from typing import Dict, List, Optional, Callable

from ghoshell.contracts import Cache
from ghoshell.framework.contracts import RuntimeDriver
from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.ghost import *
from ghoshell.messages import Tasked
from ghoshell.utils import InstanceCount


class RuntimeImpl(Runtime):

    def __init__(
            self,
            driver: RuntimeDriver,
            config: GhostConfig,
            clone_id: str,
            session_id: str,
            pid: str,
            new_pid: Callable[[], str],
    ):
        self._clone_id = clone_id
        self._driver: RuntimeDriver = driver
        self._session_id: str = session_id
        self._config = config

        # init root
        self._root_url: URL = URL(**config.root_url.model_dump())

        # 缓存数据的初始化.
        self._cached_tasks: Dict[str, Dict[str, Task]] = {}
        self._cached_processes: Dict[str, Process | None] = {}
        self._origin_processes_data: Dict[str, Process | None] = {}
        self._locked: Dict[str, bool] = {}
        self._finished: bool = False

        new_process = False
        if not pid:
            # 先从 driver 里找.
            pid = driver.get_current_process_id(self._session_id)
        if not pid:
            new_process = True
            pid = new_pid()
            driver.set_current_process_id(self._session_id, pid)
        self._current_process_id = pid
        self._init_process(new_process)
        InstanceCount.add(self.__class__.__name__)

    def _init_process(self, new_process: bool):
        # 从库里读.
        # 完成初始化.
        if new_process:
            self._new_process()
            return
        process = self.get_process(self._current_process_id)
        if not process:
            self._new_process()
        return

    def _new_process(self):
        process = Process.new_process(self._session_id, self._current_process_id, parent_id=None)
        self.store_process(process)

    def get_process(self, pid: str | None = None) -> Process | None:
        pid = pid if pid else self._current_process_id
        if pid not in self._cached_processes:
            self._init_cached_process(pid)
        return self._cached_processes[pid]

    def _init_cached_process(self, pid: str) -> None:
        process_data = self._get_origin_process(pid)
        if process_data is None:
            self._cached_processes[pid] = None
        else:
            process = process_data.new_round()
            self._cached_processes[pid] = process

    def _get_origin_process(self, pid: str) -> Process | None:
        if pid not in self._origin_processes_data:
            process_data = self._driver.get_process_data(self.session_id, pid)
            self._origin_processes_data[pid] = process_data
        return self._origin_processes_data[pid]

    def remove_process(self, process: Process) -> None:
        pid = process.pid
        del self._cached_processes[pid]
        del self._origin_processes_data[pid]
        # remove
        self._driver.remove_process(self.session_id, pid)

    def fetch_task(self, tid: str) -> Optional[Task]:
        process = self.current_process()
        # is not instanced
        return process.get_task(tid)

    def store_task(self, *tasks: Task) -> None:
        process = self.current_process()
        process.store_task(*tasks)

    def instance_task(self, ptr: Task) -> Task:
        tid = ptr.tid
        if ptr.is_long_term:
            tasked = self._driver.get_task_data(self.session_id, self._current_process_id, tid)
            if tasked is not None:
                ptr.merge_tasked(tasked)
        return ptr

    #
    # def fetch_long_term_task(self, tid: str, pid: str | None = None) -> Optional[Task]:
    #     pid = pid if pid else self._current_process_id
    #     if pid not in self._cached_tasks:
    #         self._cached_tasks[pid] = {}
    #     cached_tasks = self._cached_tasks[pid]
    #     if tid not in cached_tasks:
    #         got = self._driver.get_task_data(self.session_id, pid, tid)
    #         got_task = None
    #         if got is not None:
    #             got_task = Task(**got)
    #         cached_tasks[tid] = got_task
    #     return cached_tasks[tid]
    #
    # def store_long_term_task(self, task: Task, pid: str | None = None) -> None:
    #     pid = pid if pid else self._current_process_id
    #     if pid not in self._cached_tasks:
    #         self._cached_tasks[pid] = {}
    #     self._cached_tasks[pid][task.tid] = task

    def lock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._current_process_id
        # 一个 runtime 只锁一次, 避免重复调用方法时死锁.
        if process_id in self._locked:
            return self._locked.get(process_id, False)

        lock_overdue = self._config.process_lock_overdue
        locked = self._driver.lock_process(self.session_id, process_id, lock_overdue)
        self._locked[process_id] = locked
        return locked

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
        return self._driver.unlock_process(self.session_id, process_id)

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
        max_task = self._config.process_max_tasks

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
        # 得到需要 gc 的 tasks
        gc_tasks = self._gc_process(process)
        # todo: gc 的 tasks 要干什么?
        saving: Dict[str, Tasked] = {}
        for task in process.tasks:
            # 拥有长期记忆的 task 要通过长期记忆来读取.
            if task.is_long_term and task.vars is not None:
                saving[task.tid] = task.to_tasked()
                task.instanced = False
                task.vars = None

        # 保存 process 的数据.
        root_task = process.get_task(process.root)
        process_overdue = root_task.overdue
        if process_overdue <= 0:
            process_overdue = self._config.process_default_overdue

        # 删除 process 记忆. 保留长程任务.
        self._driver.save_task_data(process.sid, process.pid, saving)
        if process.quiting:
            self._driver.remove_process(process.sid, process.pid)
        else:
            self._driver.save_process_data(process.sid, process.pid, process, process_overdue)

    def finish(self) -> None:
        if self._finished:
            return
        self._save_all()
        self._finished = True

    def destroy(self) -> None:
        del self._driver
        del self._cached_processes
        del self._cached_tasks
        del self._origin_processes_data
        del self._session_id
        del self._current_process_id
        del self._locked
        del self._finished

    def __del__(self):
        InstanceCount.rm(self.__class__.__name__)


class CacheRuntimeDriver(RuntimeDriver):

    def __init__(self, cache: Cache):
        self._cache = cache

    def get_current_process_id(self, session_id: str) -> str | None:
        key = self._get_process_id_key(session_id)
        return self._cache.get(key)

    def set_current_process_id(self, session_id: str, process_id: str) -> None:
        key = self._get_process_id_key(session_id)
        self._cache.set(key, process_id, )

    @staticmethod
    def _get_process_id_key(session_id: str):
        return f"runtime:session:{session_id}:process_id"

    @staticmethod
    def _get_process_key(session_id: str, process_id: str):
        return f"runtime:session:{session_id}:process:{process_id}"

    @staticmethod
    def _get_task_key(session_id: str, tid: str):
        # 暂时定义为 session 级别的.
        return f"runtime:session:{session_id}:task:{tid}"

    @staticmethod
    def _get_locker_key(session_id: str, process_id: str):
        return f"runtime:session:{session_id}:process:{process_id}:locker"

    def get_process_data(self, session_id: str, process_id: str) -> Process | None:
        key = self._get_process_key(session_id, process_id)
        val = self._cache.get(key)
        if val is not None:
            return Process(**json.loads(val))
        return None

    def save_process_data(self, session_id: str, process_id: str, data: Process, overdue: int):
        #  这里需要实现特殊的序列化逻辑为好.
        data_as_dict = data.to_saving_dict()
        saving = json.dumps(data_as_dict)
        key = self._get_process_key(session_id, process_id)
        overdue = overdue if overdue > 0 else 0
        self._cache.set(key, saving, overdue)

    def get_task_data(self, session_id: str, process_id: str, task_id: str) -> Tasked | None:
        key = self._get_task_key(session_id, task_id)
        val = self._cache.get(key)
        if val is not None:
            try:
                loads = json.loads(val)
                return Tasked(**loads)
            except AttributeError:
                return None
        return None

    def save_task_data(self, session_id: str, process_id: str, data: Dict[str, Tasked]):
        for tid in data:
            key = self._get_task_key(session_id, tid)
            tasked = data[tid]
            task_data = tasked.model_dump()
            val = json.dumps(task_data)
            self._cache.set(key, val, tasked.overdue)

    def lock_process(self, session_id: str, process_id: str, overdue: int) -> bool:
        key = self._get_locker_key(session_id, process_id)
        return self._cache.lock(key, overdue)

    def unlock_process(self, session_id: str, process_id: str) -> bool:
        key = self._get_locker_key(session_id, process_id)
        return self._cache.unlock(key)

    def remove_process(self, session_id: str, process_id: str) -> bool:
        key = self._get_process_key(session_id, process_id)
        return self._cache.remove(key) == 1

    def remove_tasks(self, session_id: str, process_id: str, tasks: List[str]) -> int:
        keys = []
        for tid in tasks:
            key = self._get_task_key(session_id, tid)
            keys.append(key)
        return self._cache.remove(*keys)
