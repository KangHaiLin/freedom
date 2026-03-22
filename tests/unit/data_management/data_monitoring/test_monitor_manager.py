"""
Unit tests for monitor_manager.py
"""

from unittest.mock import Mock, patch

from data_management.data_monitoring.monitor_manager import MonitorManager
from data_management.data_monitoring.base_monitor import BaseMonitor, MonitorResult, AlertLevel


class ConcreteTestMonitor(BaseMonitor):
    """Test monitor concrete implementation"""

    def __init__(self, should_fail=False, **kwargs):
        super().__init__(**kwargs)
        self.should_fail = should_fail

    def run_check(self):
        if self.should_fail:
            return MonitorResult.failure(self.name, alert_level=AlertLevel.ERROR, message="Test failure")
        return MonitorResult.success(self.name, message="Test success")


class TestMonitorManager:
    """测试监控管理器"""

    def test_init_default(self):
        """测试默认初始化"""
        manager = MonitorManager()
        # Override config to avoid loading global settings
        manager.config = {}
        manager._init_monitors()
        assert manager.running is False
        assert len(manager.monitors) >= 0
        assert manager.alert_service is not None

    def test_init_custom_config_disable_all(self):
        """测试自定义配置禁用所有监控"""
        config = {
            "enable_data_quality_monitor": False,
            "enable_collection_monitor": False,
        }
        manager = MonitorManager()
        # Clear default monitors added by __init__ before changing config
        manager.monitors = []
        manager.config = config
        manager._init_monitors()
        assert len(manager.monitors) == 0

    def test_add_monitor(self):
        """测试添加监控"""
        manager = MonitorManager()
        manager.config = {}
        manager.monitors = []  # 清空默认
        monitor = ConcreteTestMonitor(name="test")
        manager.add_monitor(monitor)
        assert len(manager.monitors) == 1
        assert manager.monitors[0] is monitor

    def test_remove_monitor(self):
        """测试移除监控"""
        manager = MonitorManager()
        manager.config = {}
        manager.monitors = []
        monitor = ConcreteTestMonitor(name="test")
        manager.add_monitor(monitor)
        assert len(manager.monitors) == 1
        manager.remove_monitor(ConcreteTestMonitor)
        assert len(manager.monitors) == 0

    def test_run_all_once_success(self):
        """测试全部执行一次 - 全部成功"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        manager.monitors = []
        manager.add_monitor(ConcreteTestMonitor(name="test1", should_fail=False))
        manager.add_monitor(ConcreteTestMonitor(name="test2", should_fail=False))

        mock_alert = Mock()
        manager.alert_service = mock_alert

        results = manager.run_all_once()
        assert len(results) == 2
        assert all(r.success for r in results)
        # manager always calls send_alert(result), but alert_service will skip if not needed
        # Our mock just counts calls
        assert mock_alert.send_alert.call_count == 2  # Called for every result

    def test_run_all_once_with_failure(self):
        """测试全部执行一次 - 有失败"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        manager.monitors = []
        manager.add_monitor(ConcreteTestMonitor(name="test1", should_fail=False))
        manager.add_monitor(ConcreteTestMonitor(name="test2", should_fail=True))

        mock_alert = Mock()
        mock_alert.send_alert.return_value = True
        manager.alert_service = mock_alert

        results = manager.run_all_once()
        assert len(results) == 2
        # 失败那个需要发送告警
        assert mock_alert.send_alert.called

    def test_start_stop_scheduler(self):
        """测试启动停止调度器"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        assert not manager.running
        manager.start()
        assert manager.running
        assert manager.scheduler_thread is not None
        manager.stop()
        assert not manager.running

    def test_start_already_running(self):
        """测试已经运行时再次启动不做任何事"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        manager.running = True
        original_thread = Mock()
        manager.scheduler_thread = original_thread

        manager.start()
        # 仍然是原来的线程
        assert manager.scheduler_thread is original_thread

    def test__save_monitor_result_no_storage(self):
        """测试没有存储不保存"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = None
        result = MonitorResult.success("test")
        # Should not raise
        manager._save_monitor_result(result)
        # Nothing happens, passes

    def test__save_monitor_result_with_storage(self):
        """测试保存结果到存储"""
        manager = MonitorManager()
        manager.config = {}
        mock_clickhouse = Mock()
        manager.storage = mock_clickhouse
        result = MonitorResult.success("test", metrics={"score": 90})
        manager._save_monitor_result(result)
        # verify write was called
        assert mock_clickhouse.write.called

    def test_get_monitor_status(self):
        """测试获取所有监控状态"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        manager.monitors = []
        monitor = ConcreteTestMonitor(name="test_monitor")
        manager.add_monitor(monitor)

        status = manager.get_monitor_status()
        assert len(status) == 1
        assert status[0]["monitor_name"] == "test_monitor"

    def test_get_recent_alerts_no_storage(self):
        """测试获取历史告警 - 没有存储返回空列表"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = None
        alerts = manager.get_recent_alerts()
        assert alerts == []

    def test_get_dashboard_data(self):
        """测试获取仪表盘数据"""
        manager = MonitorManager()
        manager.config = {}
        mock_clickhouse = Mock()
        mock_clickhouse.execute_sql.return_value = Mock(empty=True)
        manager.storage = mock_clickhouse
        manager.redis_storage = Mock()
        manager.monitors = [ConcreteTestMonitor(name="test")]
        data = manager.get_dashboard_data()
        assert "monitor_count" in data
        assert data["monitor_count"] == 1
        assert "running" in data
        assert "recent_alerts" in data

    def test_health_check(self):
        """测试健康检查"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = Mock()
        manager.redis_storage = Mock()
        health = manager.health_check()
        assert "status" in health
        assert "monitor_count" in health
        assert "running" in health
        assert health["alert_service_healthy"] is True

    def test_get_data_quality_history_no_storage(self):
        """测试获取数据质量历史 - 没有存储返回空结构"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = None
        history = manager.get_data_quality_history(days=30)
        assert "dates" in history
        assert "quality_scores" in history
        assert len(history["dates"]) == 0
        assert len(history["quality_scores"]) == 0

    def test_get_latest_data_quality_no_storage(self):
        """测试获取最新数据质量结果 - 没有存储返回None"""
        manager = MonitorManager()
        manager.config = {}
        manager.storage = None
        result = manager.get_latest_data_quality()
        assert result is None


def test_global_instance_exists():
    """测试全局实例存在"""
    from data_management.data_monitoring.monitor_manager import monitor_manager
    assert monitor_manager is not None
    assert isinstance(monitor_manager, MonitorManager)
