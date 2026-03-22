"""
Unit tests for alert_service.py
"""

import json
from unittest.mock import Mock, patch

import pytest

from data_management.data_monitoring.alert_service import AlertService
from data_management.data_monitoring.base_monitor import AlertLevel, MonitorResult


def test_init_default():
    """测试默认初始化 - 当没有配置项时使用正确的默认值"""
    from data_management.data_monitoring.alert_service import AlertService

    # 传递配置只包含部分项，测试默认值正确 fallback
    service = AlertService(config={"enabled": True})
    # 检查默认值正确
    assert service.enabled is True
    assert service.default_channels == ["log"]
    assert "log" in service.default_channels


def test_init_custom_config():
    """测试自定义配置初始化"""
    config = {
        "enabled": False,
        "default_channels": ["log", "email"],
        "channels": {
            "email": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "smtp_user": "test@example.com",
                "smtp_password": "password",
                "receivers": ["admin@example.com"],
            }
        },
    }
    service = AlertService(config=config)
    assert service.enabled is False
    assert service.default_channels == ["log", "email"]
    assert "email" in service.channel_configs


def test_send_alert_disabled():
    """测试禁用时不发送"""
    service = AlertService(config={"enabled": False})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    assert service.send_alert(result) is False


def test_send_alert_no_need_alert():
    """测试不需要告警时不发送"""
    service = AlertService()
    result = MonitorResult.success("test")  # INFO 级别不需要告警
    assert service.send_alert(result) is False


def test_send_alert_log_channel():
    """测试日志渠道发送"""
    service = AlertService(config={"enabled": True, "default_channels": ["log"]})
    result = MonitorResult.failure("test_monitor", alert_level=AlertLevel.ERROR)
    with patch("logging.Logger.warning") as mock_log:
        success = service.send_alert(result)
        assert success is True
        # 日志会被调用
        assert mock_log.called


def test_format_alert_message():
    """测试告警消息格式化"""
    service = AlertService()
    result = MonitorResult(
        monitor_name="test_collection_monitor",
        success=False,
        message="数据采集超时",
        alert_level=AlertLevel.ERROR,
        metrics={"expected": 100, "actual": 80},
        details={"missing_symbols": ["600000.SH", "000001.SZ"]},
    )
    message = service._format_alert_message(result)
    assert "test_collection_monitor" in message
    assert "错误" in message
    assert "异常" in message
    assert "数据采集超时" in message
    assert "expected" in message
    assert "100" in message
    assert "missing_symbols" in message


def test_format_alert_message_unknown_level():
    """测试未知级别格式化"""
    service = AlertService()

    # 创建一个不存在的级别（模拟）
    class FakeAlertLevel:
        value = 999
        name = "FAKE"

    result = MonitorResult("test", success=False, level=FakeAlertLevel())
    message = service._format_alert_message(result)
    assert "未知" in message


def test_send_alert_unsupported_channel():
    """测试不支持的渠道"""
    service = AlertService(config={"enabled": True, "default_channels": ["unsupported"]})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    success = service.send_alert(result)
    assert success is False


def test_send_alert_multiple_channels_mixed_success():
    """测试多个渠道混合结果"""
    service = AlertService(config={"enabled": True, "default_channels": ["log", "unsupported"]})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    success = service.send_alert(result)
    # 一个成功一个失败，整体失败
    assert success is False


def test_send_email_alert_unconfigured():
    """测试未配置邮件告警抛出异常"""
    service = AlertService(config={"channels": {}})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    with pytest.raises(ValueError, match="邮件告警未配置"):
        service._send_email_alert(result, None)


def test_send_wecom_alert_unconfigured():
    """测试未配置企业微信告警抛出异常"""
    service = AlertService(config={"channels": {}})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    with pytest.raises(ValueError, match="企业微信告警未配置"):
        service._send_wecom_alert(result, None)


def test_send_dingtalk_alert_unconfigured():
    """测试未配置钉钉告警抛出异常"""
    service = AlertService(config={"channels": {}})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    with pytest.raises(ValueError, match="钉钉告警未配置"):
        service._send_dingtalk_alert(result, None)


def test_send_webhook_alert_unconfigured():
    """测试未配置webhook告警抛出异常"""
    service = AlertService(config={"channels": {}})
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)
    with pytest.raises(ValueError, match="Webhook告警未配置"):
        service._send_webhook_alert(result)


@patch("smtplib.SMTP_SSL")
def test_send_email_alert_success(mock_smtp):
    """测试邮件发送成功"""
    config = {
        "channels": {
            "email": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 465,
                "smtp_user": "test@example.com",
                "smtp_password": "password",
                "receivers": ["admin@example.com"],
            }
        }
    }
    service = AlertService(config=config)
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)

    mock_server = Mock()
    mock_smtp.return_value = mock_server

    service._send_email_alert(result, None)

    mock_smtp.assert_called_once_with("smtp.example.com", 465)
    mock_server.login.assert_called_once_with("test@example.com", "password")
    mock_server.sendmail.assert_called_once()
    mock_server.quit.assert_called_once()


@patch("requests.post")
def test_send_wecom_alert_success(mock_post):
    """测试企业微信发送成功"""
    mock_post.return_value.raise_for_status = Mock()
    config = {
        "channels": {
            "wecom": {
                "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=testkey",
            }
        }
    }
    service = AlertService(config=config)
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)

    service._send_wecom_alert(result, ["@all"])

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=testkey" in call_args[0][0]


@patch("requests.post")
def test_send_dingtalk_alert_success(mock_post):
    """测试钉钉发送成功"""
    mock_post.return_value.raise_for_status = Mock()
    config = {
        "channels": {
            "dingtalk": {
                "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
            }
        }
    }
    service = AlertService(config=config)
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)

    service._send_dingtalk_alert(result, None)

    mock_post.assert_called_once()


@patch("requests.post")
def test_send_webhook_alert_success(mock_post):
    """测试自定义webhook发送成功"""
    mock_post.return_value.raise_for_status = Mock()
    config = {
        "channels": {
            "webhook": {
                "url": "https://example.com/webhook",
                "headers": {"Authorization": "Bearer token"},
            }
        }
    }
    service = AlertService(config=config)
    result = MonitorResult.failure("test", alert_level=AlertLevel.ERROR)

    service._send_webhook_alert(result)

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://example.com/webhook"
    assert "Authorization" in call_args[1]["headers"]
    assert "alert" in call_args[1]["json"]


def test_send_test_alert():
    """测试发送测试告警"""
    service = AlertService(config={"enabled": True, "default_channels": ["log"]})
    with patch("logging.Logger.warning") as mock_log:
        success = service.send_test_alert()
        assert success is True
        assert mock_log.called


def test_global_instance_exists():
    """测试全局实例存在"""
    from data_management.data_monitoring.alert_service import alert_service

    assert alert_service is not None
    assert isinstance(alert_service, AlertService)
