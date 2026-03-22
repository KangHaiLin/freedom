"""
Unit tests for base_monitor.py
"""

from datetime import datetime, timedelta

import pytest

from common.exceptions import MonitorException
from data_management.data_monitoring.base_monitor import AlertLevel, BaseMonitor, MonitorResult


class TestAlertLevel:
    """测试告警级别枚举"""

    def test_comparison(self):
        """测试比较运算符"""
        info = AlertLevel.INFO
        warning = AlertLevel.WARNING
        error = AlertLevel.ERROR
        critical = AlertLevel.CRITICAL

        assert info < warning < error < critical
        assert info <= warning <= error <= critical
        assert critical > error > warning > info
        assert critical >= error >= warning >= info

    def test_name_lower(self):
        """测试小写名称属性"""
        assert AlertLevel.ERROR.name_lower == "error"
        assert AlertLevel.CRITICAL.name_lower == "critical"


class TestMonitorResult:
    """测试监控结果封装"""

    def test_init_default(self):
        """测试默认初始化"""
        result = MonitorResult("test_monitor", success=True)
        assert result.monitor_name == "test_monitor"
        assert result.success is True
        assert result.message == ""
        assert result.alert_level == AlertLevel.INFO
        assert result.level == result.alert_level
        assert result.metrics == {}
        assert result.details == {}
        assert result.timestamp is not None

    def test_init_with_level_compatibility(self):
        """测试兼容旧参数名 level"""
        result = MonitorResult("test_monitor", success=False, level=AlertLevel.CRITICAL)
        assert result.alert_level == AlertLevel.CRITICAL
        assert result.level == AlertLevel.CRITICAL

    def test_success_factory(self):
        """测试成功工厂方法"""
        result = MonitorResult.success("test_monitor", metrics={"count": 100}, message="OK")
        assert result.monitor_name == "test_monitor"
        assert result.success is True
        assert result.message == "OK"
        assert result.alert_level == AlertLevel.INFO
        assert result.metrics == {"count": 100}
        assert result.need_alert() is False

    def test_failure_factory(self):
        """测试失败工厂方法"""
        result = MonitorResult.failure("test_monitor", alert_level=AlertLevel.ERROR, message="failed")
        assert result.monitor_name == "test_monitor"
        assert result.success is False
        assert result.message == "failed"
        assert result.alert_level == AlertLevel.ERROR
        assert result.need_alert() is True

    def test_to_dict(self):
        """测试转换为字典"""
        result = MonitorResult.success(
            "test_monitor", metrics={"records": 100}, message="check passed"
        )
        dict_result = result.to_dict()

        assert dict_result["monitor_name"] == "test_monitor"
        assert dict_result["success"] is True
        assert dict_result["message"] == "check passed"
        assert dict_result["level"] == "info"
        assert dict_result["level_value"] == 0
        assert dict_result["metrics"] == {"records": 100}
        assert "timestamp" in dict_result

    def test_need_alert(self):
        """测试是否需要告警判断"""
        # INFO 不需要告警
        result_info = MonitorResult.success("test")
        assert result_info.need_alert() is False

        # WARNING 不需要告警
        result_warning = MonitorResult.failure("test", alert_level=AlertLevel.WARNING)
        assert result_warning.need_alert() is False

        # ERROR 需要告警
        result_error = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
        assert result_error.need_alert() is True

        # CRITICAL 需要告警
        result_critical = MonitorResult.failure("test", alert_level=AlertLevel.CRITICAL)
        assert result_critical.need_alert() is True


class ConcreteTestMonitor(BaseMonitor):
    """具体监控实现用于测试"""

    def __init__(self, should_fail=False, exception=False, **kwargs):
        super().__init__(**kwargs)
        self.should_fail = should_fail
        self.exception = exception

    def run_check(self):
        if self.exception:
            raise ValueError("测试异常")
        if self.should_fail:
            return MonitorResult.failure(self.name, alert_level=AlertLevel.ERROR, message="检查失败")
        return MonitorResult.success(self.name, metrics={"checked": 100})


class TestBaseMonitor:
    """测试监控抽象基类"""

    def test_init_default(self):
        """测试默认初始化"""
        monitor = ConcreteTestMonitor()
        assert monitor.name == "ConcreteTestMonitor"
        assert monitor.enabled is True
        assert monitor.interval == 60
        assert monitor.check_interval == 60
        assert monitor.alert_threshold == 3
        assert monitor.consecutive_failures_threshold == 3
        assert monitor.failure_count == 0
        assert monitor.consecutive_failures == 0
        assert monitor.last_run_time is None
        assert monitor.last_alert_time is None
        assert monitor.alert_cooldown == 300

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "enabled": False,
            "interval": 120,
            "alert_threshold": 5,
            "alert_cooldown": 600,
        }
        monitor = ConcreteTestMonitor(
            name="my_monitor",
            config=config,
            check_interval=120,
            alert_cooldown=600,
            consecutive_failures_threshold=5,
        )
        assert monitor.name == "my_monitor"
        assert monitor.enabled is False
        assert monitor.interval == 120
        assert monitor.alert_threshold == 5
        assert monitor.alert_cooldown == 600

    def test_run_disabled(self):
        """测试禁用监控直接返回成功"""
        monitor = ConcreteTestMonitor(config={"enabled": False})
        result = monitor.run()
        assert result.success is True
        assert "监控已禁用" in result.message

    def test_run_success(self):
        """测试成功运行"""
        monitor = ConcreteTestMonitor()
        result = monitor.run()
        assert result.success is True
        assert monitor.failure_count == 0
        assert monitor.consecutive_failures == 0
        assert monitor.last_run_time is not None

    def test_run_failure_once(self):
        """测试失败一次"""
        monitor = ConcreteTestMonitor(should_fail=True)
        result = monitor.run()
        assert result.success is False
        assert monitor.failure_count == 1
        assert monitor.consecutive_failures == 1
        # 未达到阈值，不应该告警
        assert result.need_send_alert is False

    def test_run_failure_reaches_threshold(self):
        """测试失败达到阈值"""
        monitor = ConcreteTestMonitor(
            should_fail=True,
            config={"alert_threshold": 3}
        )
        # 连续失败3次
        for _ in range(3):
            result = monitor.run()
        assert result.success is False
        assert monitor.failure_count == 3
        assert monitor.consecutive_failures == 3
        # 达到阈值，应该告警（首次告警）
        assert result.need_send_alert is True

    def test_run_exception(self):
        """测试执行异常"""
        monitor = ConcreteTestMonitor(exception=True)
        result = monitor.run()
        assert result.success is False
        assert "监控执行异常" in result.message
        assert monitor.failure_count == 1

    def test_success_after_failure_resets_counter(self):
        """测试失败后成功会重置计数器"""
        monitor = ConcreteTestMonitor(
            config={"alert_threshold": 3}
        )
        # 两次失败
        monitor._record_failure()
        monitor._record_failure()
        assert monitor.failure_count == 2
        # 一次成功
        monitor._record_success()
        assert monitor.failure_count == 0

    def test_should_trigger_alert(self):
        """测试是否达到告警阈值"""
        monitor = ConcreteTestMonitor(consecutive_failures_threshold=3)
        assert not monitor._should_trigger_alert()
        for _ in range(2):
            monitor._record_failure()
        assert not monitor._should_trigger_alert()
        monitor._record_failure()
        assert monitor._should_trigger_alert()

    def test_can_send_alert_first_time(self):
        """测试首次发送告警允许"""
        monitor = ConcreteTestMonitor()
        assert monitor._can_send_alert() is True

    def test_can_send_alert_after_cooldown(self):
        """测试冷却时间过后允许发送"""
        from common.utils import DateTimeUtils
        monitor = ConcreteTestMonitor(alert_cooldown=300)
        # 上次告警是10分钟前
        monitor.last_alert_time = DateTimeUtils.now() - timedelta(minutes=10)
        assert monitor._can_send_alert() is True

    def test_can_send_alert_before_cooldown(self):
        """测试冷却时间内不允许发送"""
        from common.utils import DateTimeUtils
        monitor = ConcreteTestMonitor(alert_cooldown=300)
        # 上次告警是1分钟前
        monitor.last_alert_time = DateTimeUtils.now() - timedelta(minutes=1)
        assert monitor._can_send_alert() is False

    def test_get_status(self):
        """测试获取监控状态"""
        monitor = ConcreteTestMonitor(name="test_monitor")
        status = monitor.get_status()
        assert status["monitor_name"] == "test_monitor"
        assert status["enabled"] is True
        assert status["failure_count"] == 0
        assert status["last_run_time"] is None
        assert status["last_alert_time"] is None

    def test_alert_cooldown_prevents_alert(self):
        """测试告警冷却阻止重复告警"""
        from common.utils import DateTimeUtils
        monitor = ConcreteTestMonitor(
            should_fail=True,
            config={"alert_threshold": 1},
            alert_cooldown=300,  # 冷却5分钟
        )
        # 第一次失败 - 应该告警
        result1 = monitor.run()
        assert result1.need_send_alert is True
        assert monitor.last_alert_time is not None

        # 修改当前时间到冷却时间内再次失败 - 不应该告警
        result2 = monitor.run()
        assert result2.need_send_alert is False
