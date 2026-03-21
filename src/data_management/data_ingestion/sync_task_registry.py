"""
历史数据同步任务注册模块
负责创建各类型同步任务，注册到调度器，提供手动触发入口
"""
from typing import Dict, Any, Optional
import logging

from system_management.task_scheduler.scheduler_manager import get_scheduler_manager
from system_management.task_scheduler.scheduled_task import ScheduledTask
from .historical_sync_task import (
    HistoricalSyncTask,
    DailyHistoricalSyncTask,
    Minute1HistoricalSyncTask,
    Minute5HistoricalSyncTask,
    TickHistoricalSyncTask,
)
from common.config import settings

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler_manager = get_scheduler_manager()


class SyncTaskFactory:
    """同步任务工厂"""

    _instances: Dict[str, HistoricalSyncTask] = {}

    @classmethod
    def create_daily_sync(
        cls,
        batch_size: Optional[int] = None,
        default_start_date: Optional[str] = None,
    ) -> DailyHistoricalSyncTask:
        """创建日线同步任务"""
        task = DailyHistoricalSyncTask(
            batch_size=batch_size,
            default_start_date=default_start_date,
            task_name="日线历史数据同步",
        )
        cls._instances["daily"] = task
        return task

    @classmethod
    def create_minute1_sync(
        cls,
        batch_size: Optional[int] = None,
        default_start_date: Optional[str] = None,
    ) -> Minute1HistoricalSyncTask:
        """创建1分钟线同步任务"""
        task = Minute1HistoricalSyncTask(
            batch_size=batch_size,
            default_start_date=default_start_date,
            task_name="1分钟线历史数据同步",
        )
        cls._instances["minute1"] = task
        return task

    @classmethod
    def create_minute5_sync(
        cls,
        batch_size: Optional[int] = None,
        default_start_date: Optional[str] = None,
    ) -> Minute5HistoricalSyncTask:
        """创建5分钟线同步任务"""
        task = Minute5HistoricalSyncTask(
            batch_size=batch_size,
            default_start_date=default_start_date,
            task_name="5分钟线历史数据同步",
        )
        cls._instances["minute5"] = task
        return task

    @classmethod
    def create_tick_sync(
        cls,
        batch_size: Optional[int] = None,
        default_start_date: Optional[str] = None,
    ) -> TickHistoricalSyncTask:
        """创建Tick数据同步任务"""
        task = TickHistoricalSyncTask(
            batch_size=batch_size,
            default_start_date=default_start_date,
            task_name="Tick历史数据同步",
        )
        cls._instances["tick"] = task
        return task

    @classmethod
    def get_task(cls, frequency: str) -> Optional[HistoricalSyncTask]:
        """获取已创建的任务实例"""
        return cls._instances.get(frequency)

    @classmethod
    def list_all_tasks(cls) -> Dict[str, HistoricalSyncTask]:
        """列出所有已创建的任务"""
        return cls._instances.copy()


def register_sync_tasks_to_scheduler() -> None:
    """
    根据配置将同步任务注册到调度器

    读取配置决定是否启用各频率同步和Cron表达式
    """
    # 确保调度器已初始化
    if not scheduler_manager._running:
        logger.info("调度器未启动，跳过同步任务注册")
        return

    # 日线同步配置
    if settings.enable_daily_sync:
        cron_expr = settings.daily_sync_cron
        logger.info(f"注册日线同步任务，Cron: {cron_expr}")

        def daily_sync_callback():
            task = SyncTaskFactory.create_daily_sync()
            result = task.execute()
            if result:
                logger.info(f"日线同步任务执行完成: {result.get('success', False)}")
            return result

        scheduler_manager.add_cron(
            cron_expr,
            daily_sync_callback,
            task_name="日线历史数据自动同步",
        )

    # 分钟线同步配置
    if settings.enable_minute_sync:
        cron_expr = settings.minute_sync_cron
        logger.info(f"注册分钟线同步任务，Cron: {cron_expr}")

        def minute_sync_callback():
            task = SyncTaskFactory.create_minute1_sync()
            result = task.execute()
            if result:
                logger.info(f"分钟线同步任务执行完成: {result.get('success', False)}")
            return result

        scheduler_manager.add_cron(
            cron_expr,
            minute_sync_callback,
            task_name="分钟线历史数据自动同步",
        )

    # Tick同步配置
    if settings.enable_tick_sync:
        cron_expr = settings.tick_sync_cron
        logger.info(f"注册Tick同步任务，Cron: {cron_expr}")

        def tick_sync_callback():
            task = SyncTaskFactory.create_tick_sync()
            result = task.execute()
            if result:
                logger.info(f"Tick同步任务执行完成: {result.get('success', False)}")
            return result

        scheduler_manager.add_cron(
            cron_expr,
            tick_sync_callback,
            task_name="Tick历史数据自动同步",
        )

    logger.info("同步任务注册完成")


def trigger_manual_sync(frequency: str) -> Dict[str, Any]:
    """
    手动触发一次同步

    Args:
        frequency: 频率 daily/minute1/minute5/tick

    Returns:
        同步结果字典
    """
    task: Optional[HistoricalSyncTask] = None

    if frequency == "daily":
        task = SyncTaskFactory.create_daily_sync()
    elif frequency == "minute1":
        task = SyncTaskFactory.create_minute1_sync()
    elif frequency == "minute5":
        task = SyncTaskFactory.create_minute5_sync()
    elif frequency == "tick":
        task = SyncTaskFactory.create_tick_sync()
    else:
        raise ValueError(f"不支持的频率: {frequency}")

    result = task.execute()
    return result


def get_sync_task_status() -> Dict[str, Any]:
    """
    获取所有同步任务的状态

    Returns:
        状态字典
    """
    tasks = SyncTaskFactory.list_all_tasks()
    status = {}

    for freq, task in tasks.items():
        status[freq] = {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "duration": task.duration,
            "result": task.result.to_dict() if task.result else None,
        }

    return status


# 导出
__all__ = [
    "SyncTaskFactory",
    "register_sync_tasks_to_scheduler",
    "trigger_manual_sync",
    "get_sync_task_status",
]
