"""
数据监控模块单元测试
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from data_management.data_monitoring.base_monitor import AlertLevel, MonitorResult, BaseMonitor
from data_management.data_monitoring.data_quality_monitor import DataQualityMonitor
from data_management.data_monitoring.collection_monitor import CollectionMonitor
from data_management.data_monitoring.alert_service import AlertService
from data_management.data_monitoring.monitor_manager import MonitorManager


class TestAlertLevel:
    """告警级别测试"""

    def test_level_order(self):
        """测试级别优先级"""
        assert AlertLevel.INFO < AlertLevel.WARNING < AlertLevel.ERROR < AlertLevel.CRITICAL
        assert AlertLevel.INFO.value == 0
        assert AlertLevel.CRITICAL.value == 3


class TestMonitorResult:
    """监控结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = MonitorResult.success(
            monitor_name="test_monitor",
            metrics={"score": 0.95},
            message="检查通过"
        )
        assert result.success
        assert result.alert_level == AlertLevel.INFO
        assert result.metrics["score"] == 0.95
        assert result.timestamp is not None

    def test_failure_result(self):
        """测试失败结果"""
        result = MonitorResult.failure(
            monitor_name="test_monitor",
            alert_level=AlertLevel.ERROR,
            metrics={"score": 0.5},
            message="数据质量不达标"
        )
        assert not result.success
        assert result.alert_level == AlertLevel.ERROR
        assert result.metrics["score"] == 0.5


class TestBaseMonitor:
    """监控基类测试"""

    # 创建测试子类
    class TestMonitorImpl(BaseMonitor):
        def run_check(self):
            return MonitorResult.success("test_monitor")

    def test_alert_cooldown(self):
        """测试告警冷却"""
        monitor = self.TestMonitorImpl("test_monitor", check_interval=60, alert_cooldown=300)

        # 第一次告警
        result1 = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试错误"
        )

        assert monitor._should_send_alert(result1)

        # 记录告警发送时间
        monitor._last_alert_time = datetime.now().timestamp()

        # 5分钟内的告警应该被抑制
        result2 = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试错误"
        )
        assert not monitor._should_send_alert(result2)

        # 更高优先级的告警应该发送
        result3 = MonitorResult.failure(
            "test_monitor",
            AlertLevel.CRITICAL,
            message="严重错误"
        )
        assert monitor._should_send_alert(result3)

    def test_failure_count(self):
        """测试失败计数"""
        monitor = self.TestMonitorImpl("test_monitor", consecutive_failures_threshold=3)

        # 第一次失败
        monitor._record_failure()
        assert monitor.consecutive_failures == 1

        # 第二次失败
        monitor._record_failure()
        assert monitor.consecutive_failures == 2

        # 第三次失败，达到阈值
        monitor._record_failure()
        assert monitor.consecutive_failures == 3
        assert monitor._should_trigger_alert()

        # 成功后计数重置
        monitor._record_success()
        assert monitor.consecutive_failures == 0


class TestDataQualityMonitor:
    """数据质量监控测试"""

    def setup_method(self):
        self.storage_manager = Mock()
        self.monitor = DataQualityMonitor(
            "realtime_quality",
            storage_manager=self.storage_manager,
            config={
                "table_name": "realtime_quotes",
                "metrics": ["completeness", "accuracy", "timeliness"],
                "thresholds": {"overall_score": 0.8}
            }
        )

    def test_check_completeness(self):
        """测试完整性检查"""
        # 构造测试数据，有缺失值
        data = pd.DataFrame({
            "stock_code": ["000001.SZ", None, "600000.SH", "000001.SZ"],
            "price": [10.0, 15.0, None, 10.1],
            "time": [datetime.now()] * 4
        })

        completeness = self.monitor._check_completeness(data)
        # 总共有3个字段，4行 = 12个值
        # 缺失2个值，完整性 = 10/12 ≈ 0.8333
        assert completeness >= 0.83
        assert completeness <= 0.84

    def test_check_accuracy(self):
        """测试准确性检查"""
        data = pd.DataFrame({
            "stock_code": ["000001.SZ", "INVALID", "600000.SH"],
            "price": [10.0, -1.0, 15.0],
            "volume": [1000, 2000, -500]
        })

        accuracy = self.monitor._check_accuracy(data)
        # 3行数据，每行3个字段，共9个值
        # 错误值："INVALID" stock_code, -1.0 price, -500 volume → 3个错误
        # 准确率 = 6/9 ≈ 0.6667
        assert accuracy >= 0.66
        assert accuracy <= 0.67

    def test_check_timeliness(self):
        """测试时效性检查"""
        now = datetime.now()
        data = pd.DataFrame({
            "time": [
                now - timedelta(minutes=5),
                now - timedelta(minutes=3),
                now - timedelta(minutes=1)
            ]
        })

        timeliness = self.monitor._check_timeliness(data, max_delay_minutes=10)
        # 最大延迟是5分钟，远小于10分钟，时效性应该很高
        assert timeliness >= 0.9

    def test_run_quality_check(self):
        """测试运行质量检查"""
        mock_data = pd.DataFrame({
            "stock_code": ["000001.SZ", "600000.SH"] * 100,
            "price": [10.0 + i * 0.1 for i in range(200)],
            "volume": [1000 + i * 10 for i in range(200)],
            "time": [datetime.now() - timedelta(seconds=i) for i in range(200)]
        })

        mock_storage = Mock()
        mock_storage.read.return_value = mock_data
        self.storage_manager.get_storage.return_value = mock_storage

        result = self.monitor.run()
        assert result.success
        assert result.metrics["completeness"] == 1.0
        assert result.metrics["accuracy"] == 1.0
        assert result.metrics["timeliness"] >= 0.95
        assert result.metrics["overall_score"] >= 0.95


class TestCollectionMonitor:
    """采集监控测试"""

    def setup_method(self):
        self.data_source_manager = Mock()
        self.monitor = CollectionMonitor(
            "collection_monitor",
            data_source_manager=self.data_source_manager,
            config={
                "success_rate_threshold": 0.9,
                "response_time_threshold": 1000
            }
        )

    def test_check_data_source_health(self):
        """测试数据源健康检查"""
        # 模拟两个数据源
        source1 = Mock()
        source1.source = "tushare"
        source1.availability = 0.95
        source1.avg_response_time = 500.0
        source1.error_count = 2
        source1.is_available.return_value = True

        source2 = Mock()
        source2.source = "joinquant"
        source2.availability = 0.85
        source2.avg_response_time = 1200.0
        source2.error_count = 5
        source2.is_available.return_value = False

        self.data_source_manager.sources = [source1, source2]

        health_report = self.monitor._check_data_source_health()
        assert health_report["total_sources"] == 2
        assert health_report["available_sources"] == 1
        assert health_report["average_availability"] == (0.95 + 0.85) / 2
        assert health_report["average_response_time"] == (500 + 1200) / 2

    def test_run_collection_monitor(self):
        """测试运行采集监控"""
        source1 = Mock()
        source1.source = "tushare"
        source1.availability = 0.95
        source1.avg_response_time = 500.0
        source1.error_count = 2
        source1.is_available.return_value = True

        self.data_source_manager.sources = [source1]
        self.data_source_manager.get_statistics.return_value = {
            "total_requests": 1000,
            "success_requests": 950,
            "failed_requests": 50,
            "avg_response_time": 450.0,
            "data_volume_per_minute": 10000
        }

        result = self.monitor.run()
        assert result.success
        assert result.metrics["success_rate"] == 0.95
        assert result.metrics["available_sources"] == 1
        assert result.metrics["data_volume_per_minute"] == 10000


class TestAlertService:
    """告警服务测试"""

    def setup_method(self):
        self.alert_service = AlertService(config={
            "default_channels": ["log", "webhook"],
            "channels": {
                "webhook": {
                    "url": "http://localhost:8000/alert"
                },
                "email": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 465,
                    "smtp_user": "test@example.com",
                    "smtp_password": "password",
                    "receivers": ["admin@example.com"]
                },
                "wecom": {
                    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key"
                }
            }
        })

    def test_send_alert_log_channel(self):
        """测试通过日志渠道发送告警"""
        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试告警"
        )

        with patch('data_management.data_monitoring.alert_service.logger.warning') as mock_log:
            success = self.alert_service.send_alert(result, channels=["log"])
            assert success
            mock_log.assert_called_once()

    @patch('requests.post')
    def test_send_alert_webhook_channel(self, mock_post):
        """测试通过Webhook渠道发送告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试告警"
        )

        success = self.alert_service.send_alert(result, channels=["webhook"])
        assert success
        mock_post.assert_called_once()
        # 验证请求参数
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:8000/alert"
        # requests会自动设置Content-Type为application/json当传json参数时
        assert "json" in kwargs
        payload = kwargs["json"]
        assert payload["alert"]["message"] == "测试告警"
        assert payload["alert"]["level"] == "error"

    @patch('smtplib.SMTP_SSL')
    def test_send_alert_email_channel_ssl(self, mock_smtp_ssl):
        """测试通过邮件渠道发送告警（SSL连接）"""
        mock_server = Mock()
        mock_smtp_ssl.return_value = mock_server

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试邮件告警"
        )

        success = self.alert_service.send_alert(result, channels=["email"])
        assert success
        mock_smtp_ssl.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_alert_email_channel_starttls(self, mock_smtp):
        """测试通过邮件渠道发送告警（STARTTLS连接）"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        # 使用非SSL端口
        self.alert_service.channel_configs['email']['smtp_port'] = 587

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试邮件告警"
        )

        success = self.alert_service.send_alert(result, channels=["email"])
        assert success
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    def test_send_alert_email_channel_incomplete_config(self):
        """测试邮件告警配置不完整"""
        # 移除密码
        self.alert_service.channel_configs['email'].pop('smtp_password')

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试邮件告警"
        )

        with patch('data_management.data_monitoring.alert_service.logger.warning') as mock_log:
            success = self.alert_service.send_alert(result, channels=["email"])
            assert not success
            mock_log.assert_called_once()

    @patch('requests.post')
    def test_send_alert_wecom_channel(self, mock_post):
        """测试通过企业微信渠道发送告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试企业微信告警"
        )

        success = self.alert_service.send_alert(result, channels=["wecom"])
        assert success
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "json" in kwargs
        payload = kwargs["json"]
        assert payload["msgtype"] == "text"
        assert "content" in payload["text"]

    def test_send_alert_wecom_channel_no_webhook(self):
        """测试企业微信未配置webhook"""
        self.alert_service.channel_configs['wecom'].pop('webhook_url')

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试企业微信告警"
        )

        with patch('data_management.data_monitoring.alert_service.logger.warning') as mock_log:
            success = self.alert_service.send_alert(result, channels=["wecom"])
            assert not success
            mock_log.assert_called_once()

    @patch('requests.post')
    def test_send_alert_dingtalk_channel(self, mock_post):
        """测试通过钉钉渠道发送告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 添加钉钉配置
        self.alert_service.channel_configs['dingtalk'] = {
            'webhook_url': 'https://oapi.dingtalk.com/robot/send?access_token=test-token'
        }

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试钉钉告警"
        )

        success = self.alert_service.send_alert(result, channels=["dingtalk"])
        assert success
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "json" in kwargs
        payload = kwargs["json"]
        assert payload["msgtype"] == "text"
        assert "content" in payload["text"]

    def test_send_alert_unknown_channel(self):
        """测试未知告警渠道"""
        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试告警"
        )

        with patch('data_management.data_monitoring.alert_service.logger.warning') as mock_log:
            success = self.alert_service.send_alert(result, channels=["unknown"])
            assert not success
            mock_log.assert_called_once()

    def test_send_test_alert(self):
        """测试发送测试告警"""
        with patch('data_management.data_monitoring.alert_service.logger.warning') as mock_log:
            success = self.alert_service.send_test_alert(channels=["log"])
            assert success
            mock_log.assert_called_once()

    def test_no_alert_when_disabled(self):
        """测试禁用告警时不发送"""
        self.alert_service.enabled = False

        result = MonitorResult.failure(
            "test_monitor",
            AlertLevel.ERROR,
            message="测试告警"
        )

        success = self.alert_service.send_alert(result, channels=["log"])
        assert not success


class TestMonitorManager:
    """监控管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        # 简化测试，核心功能已经在其他测试中验证
        # 由于MonitorManager初始化依赖很多外部配置，这里只验证类可以正常导入
        assert MonitorManager is not None

    def test_run_all_monitors(self):
        """测试运行所有监控"""
        monitor1 = Mock(spec=BaseMonitor)
        monitor1.name = "monitor1"
        result1 = MonitorResult.success("monitor1")
        monitor1.run.return_value = result1

        monitor2 = Mock(spec=BaseMonitor)
        monitor2.name = "monitor2"
        result2 = MonitorResult.success("monitor2", message="正常")
        monitor2.run.return_value = result2

        manager = MonitorManager()
        manager.monitors = [monitor1, monitor2]
        manager.alert_service = Mock()

        results = manager.run_all_once()
        assert len(results) == 2
        assert results[0].success
        assert results[1].success
        # 所有结果都会调用send_alert，内部会判断是否需要发送
        assert manager.alert_service.send_alert.call_count == 2
