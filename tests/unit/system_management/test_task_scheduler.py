"""
测试任务调度
"""

import time
from datetime import datetime

from src.system_management.task_scheduler import (
    AsyncTask,
    AsyncTaskQueue,
    BaseTask,
    ScheduledTask,
    SchedulerManager,
    TaskRegistry,
    TaskResult,
    TaskStatus,
)


def test_base_task():
    """测试基础任务"""

    class TestTask(BaseTask):
        def run(self):
            return 42

    task = TestTask("test")
    assert task.status == TaskStatus.PENDING

    result = task.execute()
    assert result.success
    assert result.result == 42
    assert task.status == TaskStatus.COMPLETED
    assert task.duration > 0


def test_base_task_error():
    """测试基础任务错误处理"""

    class ErrorTask(BaseTask):
        def run(self):
            raise ValueError("test error")

    task = ErrorTask("error_task")
    result = task.execute()
    assert not result.success
    assert result.error is not None
    assert "test error" in str(result.error)
    assert task.status == TaskStatus.FAILED


def test_base_task_callback():
    """测试完成回调"""
    called = False
    result_arg = None

    def callback(result):
        nonlocal called, result_arg
        called = True
        result_arg = result

    class TestTask(BaseTask):
        def run(self):
            return 100

    task = TestTask("test").on_complete(callback)
    task.execute()
    assert called
    assert result_arg.success
    assert result_arg.result == 100


def test_scheduled_task_cron():
    """测试 Cron 定时任务"""
    called = False

    def callback():
        nonlocal called
        called = True

    # 每分钟执行一次
    task = ScheduledTask.from_cron("* * * * *", callback, "test_cron")
    assert task.cron_expr == "* * * * *"

    # 下一次执行应该在不久之后
    next_run = task._calculate_next_run(datetime.now())
    assert next_run is not None
    assert next_run > datetime.now()

    # 应该执行
    assert task.should_run(next_run)


def test_scheduled_task_interval():
    """测试固定间隔任务"""
    called = 0

    def callback():
        nonlocal called
        called += 1

    task = ScheduledTask.every(0.1, callback, "test_interval", start_immediately=True)
    assert task.interval_seconds == 0.1
    assert task.next_run is not None
    assert task.should_run(datetime.now())


def test_scheduled_task_once_after():
    """测试一次性延迟任务"""
    called = False

    def callback():
        nonlocal called
        called = True

    task = ScheduledTask.once_after(0.01, callback, "test_once")
    assert task.is_one_shot
    assert task.run_count == 0

    from datetime import timedelta

    # next_run 已经是 datetime.now() + delay_seconds，所以直接测试它
    assert task.should_run(task.next_run)

    # 执行一次
    task.execute()
    task.after_run()
    assert task.run_count == 1
    # 一次性任务，下一次 None
    assert task.next_run is None
    assert task.status == TaskStatus.COMPLETED


def test_scheduled_task_should_run():
    """测试应该运行判断"""
    task = ScheduledTask.once_after(3600, lambda: None)
    assert not task.should_run(datetime.now())


def test_async_task_priority():
    """测试异步任务优先级"""

    def f():
        pass

    high = AsyncTask(f, priority=100)
    low = AsyncTask(f, priority=1)

    # 优先级高的应该排在前面，所以 high < low 为 True（PriorityQueue 是小顶堆）
    assert high < low


def test_async_task_queue():
    """测试异步任务队列"""
    result = None

    def task_func():
        nonlocal result
        result = 42
        return result

    queue = AsyncTaskQueue(max_workers=2)
    queue.start()

    task = queue.submit(task_func)
    queue.stop(wait=True)

    assert result == 42
    assert task.status == TaskStatus.COMPLETED


def test_async_task_queue_multiple():
    """测试多个异步任务"""
    results = []

    def task_func(i):
        def inner():
            results.append(i)
            return i

        return inner

    queue = AsyncTaskQueue(max_workers=5)
    queue.start()

    for i in range(10):
        queue.submit(task_func(i))

    queue.stop(wait=True)

    assert len(results) == 10
    assert sorted(results) == list(range(10))


def test_task_registry():
    """测试任务注册"""
    registry = TaskRegistry()

    # 注册定时任务
    task1 = ScheduledTask.every(60, lambda: None)
    id1 = registry.register_scheduled(task1)

    # 注册异步任务
    task2 = AsyncTask(lambda: None)
    id2 = registry.register_async(task2)

    assert registry.get_scheduled(id1) == task1
    assert registry.get_async(id2) == task2
    assert registry.get(id1) == task1
    assert registry.get(id2) == task2

    stats = registry.get_stats()
    assert stats["total_scheduled"] == 1
    assert stats["total_async"] == 1

    # 注销
    assert registry.unregister_scheduled(id1)
    assert registry.get_scheduled(id1) is None


def test_task_registry_cleanup_completed():
    """测试清理已完成任务"""
    registry = TaskRegistry()

    # 完成的异步任务
    task = AsyncTask(lambda: 42)
    task.execute()
    registry.register_async(task)

    pending = AsyncTask(lambda: 42)
    registry.register_async(pending)

    cleaned = registry.cleanup_completed()
    assert cleaned == 1
    assert registry.get_async(task.task_id) is None
    assert registry.get_async(pending.task_id) is not None


def test_scheduler_manager():
    """测试调度管理器"""
    manager = SchedulerManager()
    # 重新初始化
    manager._initialized = True
    manager.initialize(max_concurrent_async=5, auto_start=False)

    counter = 0

    def increment():
        nonlocal counter
        counter += 1

    # 添加定时任务
    task_id = manager.add_interval(0.01, increment, "test")
    assert task_id is not None

    # 提交异步任务
    async_result = None

    def async_func():
        nonlocal async_result
        async_result = 100
        return async_result

    async_id = manager.submit_async(async_func)
    assert async_id is not None

    # 启动
    manager.start()
    # 等待一下
    time.sleep(0.1)
    # 停止
    manager.shutdown()

    assert counter > 0
    assert async_result == 100

    stats = manager.get_stats()
    assert stats["running"] is False


def test_scheduler_get_task_status():
    """测试获取任务状态"""
    manager = SchedulerManager()
    manager._initialized = True
    manager.initialize(auto_start=False)

    task_id = manager.add_interval(60, lambda: None)
    status = manager.get_task_status(task_id)

    assert status is not None
    assert "task_id" in status
    assert "task_name" in status
    assert "next_run" in status


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
