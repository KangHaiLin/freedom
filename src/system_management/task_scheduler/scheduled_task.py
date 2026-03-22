"""
任务调度 - 定时任务
支持 Cron 表达式、固定间隔、一次性延迟执行
"""

from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from croniter import croniter

from .base_task import BaseTask, TaskResult, TaskStatus


class ScheduledTask(BaseTask):
    """
    定时任务
    支持：
    - Cron 表达式
    - 固定间隔执行
    - 一次性延迟执行
    """

    def __init__(
        self,
        task_name: Optional[str] = None,
        cron_expr: Optional[str] = None,
        interval_seconds: Optional[float] = None,
        delay_seconds: Optional[float] = None,
        start_time: Optional[datetime] = None,
        callback: Optional[Callable[[], Any]] = None,
    ):
        """
        初始化定时任务

        Args:
            task_name: 任务名称
            cron_expr: Cron 表达式，例如 "0 0 * * *" 表示每天凌晨
            interval_seconds: 固定间隔秒数，每间隔多久执行一次
            delay_seconds: 延迟秒数后只执行一次
            start_time: 开始时间，为 None 表示立即
            callback: 执行回调函数
        """
        super().__init__(task_name)
        self.cron_expr = cron_expr
        self.interval_seconds = interval_seconds
        self.delay_seconds = delay_seconds
        self.start_time = start_time
        self.callback = callback

        # 调度信息
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.next_run: Optional[datetime] = self._calculate_next_run(datetime.now())

    def _calculate_next_run(self, base_time: datetime) -> Optional[datetime]:
        """计算下一次执行时间"""
        if self.cron_expr is not None:
            # Cron 表达式
            if not croniter.is_valid(self.cron_expr):
                return None
            iter = croniter(self.cron_expr, base_time)
            return iter.get_next(datetime)

        elif self.interval_seconds is not None:
            # 固定间隔
            if self.last_run is None:
                # 第一次执行
                if self.start_time is not None:
                    return self.start_time
                return base_time + timedelta(seconds=self.interval_seconds)
            else:
                return self.last_run + timedelta(seconds=self.interval_seconds)

        elif self.delay_seconds is not None:
            # 一次性延迟执行
            if self.run_count > 0:
                return None  # 已经执行过，不再执行
            if self.start_time is not None:
                return self.start_time
            return base_time + timedelta(seconds=self.delay_seconds)

        return None

    def should_run(self, now: datetime) -> bool:
        """检查是否应该执行"""
        if self.next_run is None:
            return False
        if self.status == TaskStatus.RUNNING:
            return False
        return now >= self.next_run

    def run(self) -> Any:
        """执行任务"""
        if self.callback is not None:
            return self.callback()
        return None

    def after_run(self) -> None:
        """执行完成后更新下一次执行时间"""
        self.last_run = datetime.now()
        self.run_count += 1
        self.next_run = self._calculate_next_run(datetime.now())

        # 如果是一次性任务且已经执行，标记为完成
        if self.delay_seconds is not None and self.run_count >= 1:
            self.status = TaskStatus.COMPLETED

    @classmethod
    def from_cron(
        cls,
        cron_expr: str,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
    ) -> "ScheduledTask":
        """从 Cron 表达式创建定时任务"""
        return cls(
            task_name=task_name,
            cron_expr=cron_expr,
            callback=callback,
        )

    @classmethod
    def every(
        cls,
        interval_seconds: float,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
        start_immediately: bool = True,
    ) -> "ScheduledTask":
        """创建固定间隔定时任务"""
        start_time = datetime.now() if start_immediately else None
        return cls(
            task_name=task_name,
            interval_seconds=interval_seconds,
            start_time=start_time,
            callback=callback,
        )

    @classmethod
    def once_after(
        cls,
        delay_seconds: float,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
    ) -> "ScheduledTask":
        """创建一次性延迟任务"""
        return cls(
            task_name=task_name,
            delay_seconds=delay_seconds,
            callback=callback,
        )

    @property
    def is_one_shot(self) -> bool:
        """是否是一次性任务"""
        return self.delay_seconds is not None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "status": self.status.value,
            "cron_expr": self.cron_expr,
            "interval_seconds": self.interval_seconds,
            "delay_seconds": self.delay_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "duration": self.duration,
        }
