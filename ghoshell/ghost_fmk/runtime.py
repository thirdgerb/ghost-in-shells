from __future__ import annotations

import json
from collections import namedtuple
from typing import Dict, List

from ghoshell.ghost import *
from ghoshell.ghost_fmk.config import GhostConfig
from ghoshell.ghost_fmk.contracts import RuntimeDriver

TaskData = namedtuple("TaskData", "data overdue")


class RuntimeImpl(Runtime):

    def __init__(self, driver: RuntimeDriver, ctx: Context, config: GhostConfig):
        self._driver: RuntimeDriver = driver
        self._session_id: str = ctx.session.session_id
        self._config = config

        # init root
        root = ctx.clone.root
        self._root_url: URL = URL(**root.dict())

        # 缓存数据的初始化.
        self._cached_tasks: Dict[str, Dict[str, Task]] = {}
        self._cached_processes: Dict[str, Process | None] = {}
        self._origin_processes: Dict[str, Dict | None] = {}
        self._locked: Dict[str, bool] = {}

        pid = ctx.input.trace.process_id
        if pid:
            self._init_process(ctx.session, pid)
        else:
            self._init_process(ctx.session, None)

    def _init_process(self, session: Session, pid: str | None):
        if pid is None:
            process_id = session.new_process_id()
        else:
            process_id = pid
        self._current_process_id = process_id
        process = None
        if pid is not None:
            # 从库里读.
            process = self.get_process(process_id)
        # 完成初始化.
        if process is None:
            process = Process.new_process(self._session_id, self._current_process_id, parent_id=None)
        self.store_process(process)

    def get_process(self, pid: str | None = None) -> Process | None:
        pid = pid if pid else self._current_process_id
        if pid not in self._cached_processes:
            process = None
            process_data = self._get_origin_process(pid)
            if process_data is not None:
                process = Process(**process_data)
            self._cached_processes[pid] = process
        return self._cached_processes.get(pid, None)

    def _get_origin_process(self, pid: str) -> Dict | None:
        if pid not in self._origin_processes:
            process_data = self._driver.get_process_data(self.session_id, pid)
            self._origin_processes[pid] = process_data
        return self._origin_processes[pid]

    def fetch_long_term_task(self, tid: str, pid: str | None = None) -> Optional[Task]:
        pid = pid if pid else self._current_process_id
        if pid not in self._cached_tasks:
            self._cached_tasks[pid] = {}
        cached_tasks = self._cached_tasks[pid]
        if tid not in cached_tasks:
            got = self._driver.get_task_data(self.session_id, pid, tid)
            got_task = None
            if got is not None:
                got_task = Task(**got)
            cached_tasks[tid] = got_task
        return cached_tasks[tid]

    def store_long_term_task(self, task: Task, pid: str | None = None) -> None:
        pid = pid if pid else self._current_process_id
        if pid not in self._cached_tasks:
            self._cached_tasks[pid] = {}
        self._cached_tasks[pid][task.tid] = task

    def lock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._current_process_id
        # 一个 runtime 只锁一次, 避免重复调用方法时死锁.
        if process_id in self._locked:
            return self._locked.get(process_id, False)

        locked = self._driver.lock_process(self.session_id, process_id, self._lock_overdue)
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
        #  删除掉当前状态, 相当于清空了.
        del self._cached_processes[pid]

    def _save_all(self) -> None:
        if len(self._cached_processes) == 0:
            return
        for pid in self._cached_processes:
            process = self._cached_processes[pid]
            if process is None:
                continue
            self._save_process(process)

    def _save_process(self, process: Process) -> None:
        # 记录日志
        self.logger.info(f"runtime gc process {process.pid}")

        if process.is_quiting:
            self._driver.remove_process(process.sid, process.pid)
            return

        # gc 的 task 不用删除, 自然过期.
        gc_tasks = process.gc(self._max_tasks)
        stored_tasks = self._cached_tasks.get(process.pid, {})

        # gc 的任务不保存了.
        for task in gc_tasks:
            if task.tid in stored_tasks:
                del stored_tasks[task.tid]

        # 保存 process 的数据.
        process_data = process.dict()
        process_overdue = process.root_task.overdue
        if process_overdue <= 0:
            process_overdue = self._default_overdue
        self._driver.save_process_data(process.sid, process.pid, process_data, process_overdue)

        saving_tasks = {}
        for tid in stored_tasks:
            task = stored_tasks[tid]
            if task.is_long_term:
                saving_tasks[tid] = TaskData(data=task.dict(), overdue=task.overdue)
        self._driver.save_task_data(process.sid, process.pid, saving_tasks)

    def finish(self, failed: bool = False) -> None:
        if not failed:
            self._save_all()

        del self._driver
        del self._cached_processes
        del self._cached_tasks
        del self._origin_processes
        del self._session_id
        del self._current_process_id
        del self._locked
        del self.logger


class CacheRuntimeDriver(RuntimeDriver):

    def __init__(self, cache: Cache):
        self._cache = cache

    @staticmethod
    def _get_process_key(session_id: str, process_id: str):
        return f"runtime:process:{session_id}:{process_id}"

    @staticmethod
    def _get_task_key(tid: str):
        return f"runtime:task:{tid}"

    @staticmethod
    def _get_locker_key(session_id: str, process_id: str):
        return f"runtime:process:locker:{session_id}:{process_id}"

    def get_process_data(self, session_id: str, process_id: str) -> Dict | None:
        key = self._get_process_key(session_id, process_id)
        val = self._cache.get(key)
        if val is not None:
            return json.loads(val)
        return None

    def save_process_data(self, session_id: str, process_id: str, data: Dict, overdue: int):
        saving = json.dumps(data)
        key = self._get_process_key(session_id, process_id)
        overdue = overdue if overdue > 0 else 0
        self._cache.set(key, saving, overdue)

    def get_task_data(self, session_id: str, process_id: str, task_id: str) -> Dict | None:
        key = self._get_task_key(task_id)
        val = self._cache.get(key)
        if val is not None:
            return json.loads(val)
        return None

    def save_task_data(self, session_id: str, process_id: str, data: Dict[str, TaskData]):
        for tid in data:
            key = self._get_task_key(tid)
            task_data = data[tid]
            val = json.dumps(task_data.data)
            self._cache.set(key, val, task_data.overdue)

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
            key = self._get_task_key(tid)
            keys.append(key)
        return self._cache.remove(*keys)
