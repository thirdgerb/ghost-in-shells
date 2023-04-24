import uuid
from typing import Optional, Dict

from ghoshell.ghost import Context, CtxTool
from ghoshell.ghost import Runtime, Process, Task
from ghoshell.ghost import URL
from ghoshell.ghost_fmk.runtime.driver import AbsRuntimeDriver, TaskData


class IRuntime(Runtime):

    def __init__(self, driver: AbsRuntimeDriver, ctx: Context):
        self._driver: AbsRuntimeDriver = driver
        self._session_id: str = ctx.clone.session.session_id
        self.logger = ctx.logger()

        # init root
        root = ctx.clone.root
        self._root_url: URL = URL(**root.dict())

        # 缓存数据的初始化.
        self._cached_tasks: Dict[str, Dict[str, Task]] = {}
        self._cached_processes: Dict[str, Process | None] = {}
        self._origin_processes: Dict[str, Dict | None] = {}
        self._locked: Dict[str, bool] = {}

        self._process_id = ""
        self._init_process(ctx)
        config = ctx.clone.config
        self._max_tasks = config.process_max_tasks
        self._default_overdue = config.process_default_overdue
        self._lock_overdue = config.process_lock_overdue

    def _init_process(self, ctx: Context):

        process_id = ctx.input.trace.process_id
        if not process_id:
            process_id = uuid.uuid4()
        self._process_id: str = process_id

        process = self.get_process(self._process_id)
        if process is None:
            task = CtxTool.new_task_from_url(ctx, self._root_url)
            process = Process.new_process(self._session_id, task, process_id, parent_id=None)
        self.store_process(process)

    def get_process(self, pid: str | None = None) -> Process | None:
        pid = pid if pid else self._process_id
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
        pid = pid if pid else self._process_id
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
        pid = pid if pid else self._process_id
        if pid not in self._cached_tasks:
            self._cached_tasks[pid] = {}
        self._cached_tasks[pid][task.tid] = task

    def lock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._process_id
        # 一个 runtime 只锁一次, 避免重复调用方法时死锁.
        if process_id in self._locked:
            return self._locked.get(process_id, False)

        locked = self._driver.lock_process(self.session_id, process_id, self._lock_overdue)
        self._locked[process_id] = locked
        return locked

    def unlock_process(self, process_id: str | None = None) -> bool:
        if process_id is None:
            process_id = self._process_id
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
        return self._process_id

    def store_process(self, process: Process) -> None:
        self._cached_processes[process.pid] = process

    def rewind(self, pid: str | None = None) -> None:
        if pid is None:
            pid = self._process_id
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
        del self._process_id
        del self._locked
        del self.logger
