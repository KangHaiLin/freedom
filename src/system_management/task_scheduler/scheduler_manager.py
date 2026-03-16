"""
任务调度 - 调度器管理器
统一入口，启动/停止调度，注册/取消定时任务，提交异步任务
"""
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from .base_task import TaskStatus
from .scheduled_task import ScheduledTask
from .async_task import AsyncTask, AsyncTaskQueue
from .task_registry import TaskRegistry


class SchedulerManager:
    """
    调度器管理器
    - 管理定时任务调度
    - 管理异步任务队列
    - 统一入口，单例模式
    """

    _instance: Optional['SchedulerManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'SchedulerManager':
        """单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化，只执行一次"""
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._registry = TaskRegistry()
        self._async_queue: Optional[AsyncTaskQueue] = None
        self._max_concurrent_async = 10
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._check_interval = 1.0  # 每秒检查一次定时任务

    def initialize(
        self,
        max_concurrent_async: int = 10,
        check_interval_seconds: float = 1.0,
        auto_start: bool = True,
    ) -> None:
        """
        初始化调度器

        Args:
            max_concurrent_async: 最大并发异步任务数
            check_interval_seconds: 定时任务检查间隔（秒）
            auto_start: 是否自动启动
        """
        self._max_concurrent_async = max_concurrent_async
        self._check_interval = check_interval_seconds
        self._async_queue = AsyncTaskQueue(max_workers=max_concurrent_async)

        if auto_start:
            self.start()

    def add_cron(
        self,
        cron_expr: str,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
    ) -> str:
        """
        添加 Cron 定时任务

        Args:
            cron_expr: Cron 表达式
            callback: 回调函数
            task_name: 任务名称

        Returns:
            任务 ID
        """
        task = ScheduledTask.from_cron(cron_expr, callback, task_name)
        return self._registry.register_scheduled(task)

    def add_interval(
        self,
        interval_seconds: float,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
        start_immediately: bool = True,
    ) -> str:
        """
        添加固定间隔定时任务

        Args:
            interval_seconds: 间隔秒数
            callback: 回调函数
            task_name: 任务名称
            start_immediately: 是否立即开始

        Returns:
            任务 ID
        """
        task = ScheduledTask.every(
            interval_seconds,
            callback,
            task_name,
            start_immediately,
        )
        return self._registry.register_scheduled(task)

    def add_once_after(
        self,
        delay_seconds: float,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
    ) -> str:
        """
        添加一次性延迟任务

        Args:
            delay_seconds: 延迟秒数
            callback: 回调函数
            task_name: 任务名称

        Returns:
            任务 ID
        """
        task = ScheduledTask.once_after(delay_seconds, callback, task_name)
        return self._registry.register_scheduled(task)

    def remove_scheduled(self, task_id: str) -> bool:
        """移除定时任务"""
        return self._registry.unregister_scheduled(task_id)

    def submit_async(
        self,
        func: Callable[[], Any],
        priority: int = 0,
        on_complete: Optional[Callable[[Any], None]] = None,
        task_name: Optional[str] = None,
    ) -> str:
        """
        提交异步任务

        Args:
            func: 执行函数
            priority: 优先级（越大越优先）
            on_complete: 完成回调，接收结果参数
            task_name: 任务名称

        Returns:
            任务 ID
        """
        if self._async_queue is None:
            raise RuntimeError("Scheduler not initialized")

        def wrapped_on_complete(result):
            if on_complete and result.success:
                on_complete(result.result)
            elif on_complete:
                on_complete(None)

        task = self._async_queue.submit(
            func,
            priority,
            wrapped_on_complete,
            task_name,
        )
        self._registry.register_async(task)
        return task.task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._registry.get(task_id)
        if task is None:
            return None

        if isinstance(task, ScheduledTask):
            return task.to_dict()
        elif isinstance(task, AsyncTask):
            return {
                'task_id': task.task_id,
                'task_name': task.task_name,
                'status': task.status.value,
                'priority': task.priority,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'finished_at': task.finished_at.isoformat() if task.finished_at else None,
            }
        return None

    def _scheduler_loop(self) -> None:
        """调度循环"""
        while not self._stop_event.is_set():
            now = datetime.now()

            # 检查所有定时任务
            for task in self._registry.list_scheduled():
                if self._stop_event.is_set():
                    break

                if task.should_run(now):
                    # 需要执行
                    try:
                        result = task.execute()
                        # 执行完后计算下一次
                        task.after_run()

                        # 如果失败了，不处理，下一次还会尝试
                    except Exception:
                        # 确保调度不被异常中断
                        pass

            # 清理已完成的异步任务
            self._registry.cleanup_completed()

            # 等待下一次检查
            self._stop_event.wait(self._check_interval)

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return

        # 启动异步队列
        if self._async_queue is not None:
            self._async_queue.start()

        # 启动调度线程
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
        )
        self._scheduler_thread.start()
        self._running = True

    def stop(self, wait_async: bool = True) -> None:
        """停止调度器"""
        if not self._running:
            return

        self._stop_event.set()

        # 停止调度线程
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=5.0)
            self._scheduler_thread = None

        # 停止异步队列
        if self._async_queue is not None:
            self._async_queue.stop(wait=wait_async)

        self._running = False

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def get_stats(self) -> Dict[str, Any]:
        """获取调度统计信息"""
        stats = self._registry.get_stats()
        if self._async_queue:
            stats['pending_async'] = self._async_queue.pending_count
        stats['running'] = self._running
        return stats

    def list_all_tasks(self) -> Dict[str, Any]:
        """列出所有任务"""
        return {
            'scheduled': [t.to_dict() for t in self._registry.list_scheduled()],
            'async': [
                {
                    'task_id': t.task_id,
                    'task_name': t.task_name,
                    'status': t.status.value,
                    'priority': t.priority,
                }
                for t in self._registry.list_async()
            ],
        }

    def shutdown(self) -> None:
        """关闭调度器"""
        self.stop(wait_async=True)


# 全局实例
def get_scheduler_manager() -> SchedulerManager:
    """获取全局调度管理器实例"""
    return SchedulerManager()
