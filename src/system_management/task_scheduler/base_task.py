"""
任务调度 - 任务抽象基类
定义任务基础接口，错误处理，完成回调
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult:
    """任务执行结果"""

    def __init__(
        self,
        task_id: str,
        success: bool,
        result: Any = None,
        error: Optional[Exception] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.success = success
        self.result = result
        self.error = error
        self.start_time = start_time or datetime.now()
        self.end_time = end_time or datetime.now()

    @property
    def duration_seconds(self) -> float:
        """执行耗时"""
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": repr(self.result) if self.result is not None else None,
            "error": str(self.error) if self.error is not None else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
        }


class BaseTask(ABC):
    """任务抽象基类"""

    def __init__(self, task_name: Optional[str] = None):
        """初始化"""
        self.task_id = str(uuid4())
        self.task_name = task_name or self.__class__.__name__
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.result: Optional[TaskResult] = None
        self._on_complete: Optional[Callable[[TaskResult], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None

    @abstractmethod
    def run(self) -> Any:
        """
        执行任务，子类必须实现

        Returns:
            任务执行结果
        """
        pass

    def execute(self) -> TaskResult:
        """执行任务并处理错误"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        start_time = self.started_at

        try:
            result = self.run()
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

            # 完成回调
            if self._on_complete:
                try:
                    self._on_complete(task_result)
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

            # 错误回调
            if self._on_error:
                try:
                    self._on_error(e)
                except Exception:
                    pass

            return task_result

    def on_complete(self, callback: Callable[[TaskResult], None]) -> "BaseTask":
        """设置完成回调"""
        self._on_complete = callback
        return self

    def on_error(self, callback: Callable[[Exception], None]) -> "BaseTask":
        """设置错误回调"""
        self._on_error = callback
        return self

    def cancel(self) -> bool:
        """取消任务，只有挂起状态可以取消"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.CANCELLED
            return True
        return False

    @property
    def duration(self) -> Optional[float]:
        """获取执行耗时"""
        if self.started_at is None:
            return None
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()
