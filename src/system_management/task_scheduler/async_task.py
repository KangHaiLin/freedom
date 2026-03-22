"""
任务调度 - 异步任务队列
支持任务优先级、结果回调
"""

from datetime import datetime
from queue import PriorityQueue
from threading import Thread
from typing import Any, Callable, List, Optional
from uuid import uuid4

from .base_task import BaseTask, TaskResult, TaskStatus


class AsyncTask:
    """异步任务，包装可调用对象"""

    def __init__(
        self,
        func: Callable[[], Any],
        priority: int = 0,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        task_name: Optional[str] = None,
    ):
        """
        初始化异步任务

        Args:
            func: 要执行的函数
            priority: 优先级，越大越优先
            on_complete: 完成回调
            task_name: 任务名称
        """
        self.task_id = str(uuid4())
        self.func = func
        self.priority = priority  # 越大越优先
        self.on_complete = on_complete
        self.task_name = task_name or func.__name__
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.result: Optional[TaskResult] = None

    def execute(self) -> TaskResult:
        """执行任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        start_time = self.started_at

        try:
            result = self.func()
            end_time = datetime.now()
            task_result = TaskResult(
                task_id=self.task_id,
                success=True,
                result=result,
                start_time=start_time,
                end_time=end_time,
            )
            self.status = TaskStatus.COMPLETED
            self.result = task_result
            self.finished_at = end_time

            if self.on_complete:
                try:
                    self.on_complete(task_result)
                except Exception:
                    pass

            return task_result

        except Exception as e:
            end_time = datetime.now()
            task_result = TaskResult(
                task_id=self.task_id,
                success=False,
                error=e,
                start_time=start_time,
                end_time=end_time,
            )
            self.status = TaskStatus.FAILED
            self.result = task_result
            self.finished_at = end_time

            if self.on_complete:
                try:
                    self.on_complete(task_result)
                except Exception:
                    pass

            return task_result

    def __lt__(self, other: "AsyncTask") -> bool:
        """用于优先级队列比较，优先级高的排在前面"""
        # PriorityQueue 是小顶堆，所以反序比较
        return self.priority > other.priority


class AsyncTaskQueue:
    """
    异步任务队列
    支持多工作线程并发执行，优先级调度
    """

    def __init__(
        self,
        max_workers: int = 10,
    ):
        """
        初始化异步任务队列

        Args:
            max_workers: 最大并发工作线程数
        """
        self.max_workers = max_workers
        self._queue: PriorityQueue[AsyncTask] = PriorityQueue()
        self._workers: List[Thread] = []
        self._running = False
        self._stop_flag = False

    def submit(
        self,
        func: Callable[[], Any],
        priority: int = 0,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        task_name: Optional[str] = None,
    ) -> AsyncTask:
        """
        提交异步任务

        Args:
            func: 要执行的函数
            priority: 优先级，越大越优先
            on_complete: 完成回调
            task_name: 任务名称

        Returns:
            异步任务对象
        """
        task = AsyncTask(func, priority, on_complete, task_name)
        self._queue.put(task)
        return task

    def _worker_loop(self) -> None:
        """工作线程循环"""
        while not self._stop_flag:
            try:
                # 阻塞等待任务，超时 1 秒检查停止标志
                task = self._queue.get(timeout=1.0)
                task.execute()
                self._queue.task_done()
            except Exception:
                # 超时退出阻塞，继续循环检查停止标志
                pass

    def start(self) -> None:
        """启动工作线程池"""
        if self._running:
            return

        self._stop_flag = False
        self._workers.clear()

        for _ in range(self.max_workers):
            worker = Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)

        self._running = True

    def stop(self, wait: bool = True) -> None:
        """
        停止工作线程池

        Args:
            wait: 是否等待所有任务完成
        """
        if not self._running:
            return

        self._stop_flag = True

        if wait:
            # 等待队列清空
            self._queue.join()

        for worker in self._workers:
            worker.join(timeout=5.0)

        self._workers.clear()
        self._running = False

    @property
    def pending_count(self) -> int:
        """等待执行的任务数"""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
