"""
任务调度 - 任务注册
任务元数据存储，任务状态查询
"""

from typing import Dict, List, Optional, Union

from .async_task import AsyncTask
from .base_task import BaseTask, TaskStatus
from .scheduled_task import ScheduledTask


class TaskRegistry:
    """
    任务注册表
    管理所有已注册任务，支持查询状态
    """

    def __init__(self):
        """初始化"""
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._async_tasks: Dict[str, AsyncTask] = {}

    def register_scheduled(self, task: ScheduledTask) -> str:
        """注册定时任务"""
        self._scheduled_tasks[task.task_id] = task
        return task.task_id

    def unregister_scheduled(self, task_id: str) -> bool:
        """注销定时任务"""
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
            return True
        return False

    def register_async(self, task: AsyncTask) -> str:
        """注册异步任务"""
        self._async_tasks[task.task_id] = task
        return task.task_id

    def unregister_async(self, task_id: str) -> bool:
        """注销异步任务"""
        if task_id in self._async_tasks:
            del self._async_tasks[task_id]
            return True
        return False

    def get_scheduled(self, task_id: str) -> Optional[ScheduledTask]:
        """获取定时任务"""
        return self._scheduled_tasks.get(task_id)

    def get_async(self, task_id: str) -> Optional[AsyncTask]:
        """获取异步任务"""
        return self._async_tasks.get(task_id)

    def get(self, task_id: str) -> Optional[Union[ScheduledTask, AsyncTask]]:
        """获取任意类型任务"""
        if task_id in self._scheduled_tasks:
            return self._scheduled_tasks[task_id]
        if task_id in self._async_tasks:
            return self._async_tasks[task_id]
        return None

    def list_scheduled(self) -> List[ScheduledTask]:
        """列出所有定时任务"""
        return list(self._scheduled_tasks.values())

    def list_async(self) -> List[AsyncTask]:
        """列出所有异步任务"""
        return list(self._async_tasks.values())

    def list_by_status(self, status: TaskStatus) -> List[Union[ScheduledTask, AsyncTask]]:
        """按状态列出所有任务"""
        result: List[Union[ScheduledTask, AsyncTask]] = []
        for task in self._scheduled_tasks.values():
            if task.status == status:
                result.append(task)
        for task in self._async_tasks.values():
            if task.status == status:
                result.append(task)
        return result

    def get_stats(self) -> Dict[str, int]:
        """获取注册统计"""
        stats: Dict[str, int] = {}

        # 定时任务统计
        scheduled_stats: Dict[str, int] = {}
        for status in TaskStatus:
            count = sum(1 for t in self._scheduled_tasks.values() if t.status == status)
            scheduled_stats[status.value] = count
        stats["scheduled"] = scheduled_stats

        # 异步任务统计
        async_stats: Dict[str, int] = {}
        for status in TaskStatus:
            count = sum(1 for t in self._async_tasks.values() if t.status == status)
            async_stats[status.value] = count
        stats["async"] = async_stats

        stats["total_scheduled"] = len(self._scheduled_tasks)
        stats["total_async"] = len(self._async_tasks)
        stats["total"] = len(self._scheduled_tasks) + len(self._async_tasks)

        return stats

    def cleanup_completed(self) -> int:
        """清理已完成的异步任务"""
        to_remove: List[str] = []
        for task_id, task in self._async_tasks.items():
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                to_remove.append(task_id)

        for task_id in to_remove:
            del self._async_tasks[task_id]

        return len(to_remove)
