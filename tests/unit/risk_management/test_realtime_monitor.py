"""
Unit tests for realtime monitor
"""

from datetime import datetime, timedelta

import pytest

from src.risk_management.realtime_monitor.alert_generator import AlertGenerator, AlertLevel
from src.risk_management.realtime_monitor.risk_scanner import RealtimeRiskScanner
from src.risk_management.rule_engine.rule_executor import RuleExecutor
from src.risk_management.rule_engine.rule_manager import RuleManager


def test_alert_generator_deduplication():
    """Test alert deduplication"""
    generator = AlertGenerator(dedup_interval_minutes=5)

    # First alert
    alert1 = generator.generate(
        level=AlertLevel.WARNING,
        message="Test warning",
        data={"key": "value"},
        risk_type="test",
    )

    assert alert1 is not None

    # Second alert same event should be suppressed
    alert2 = generator.generate(
        level=AlertLevel.WARNING,
        message="Test warning",
        data={"key": "value"},
        risk_type="test",
    )

    assert alert2 is None  # Suppressed

    # Different data should not be suppressed
    alert3 = generator.generate(
        level=AlertLevel.WARNING,
        message="Test warning 2",
        data={"key": "value2"},
        risk_type="test",
    )

    assert alert3 is not None


def test_alert_generator_get_recent():
    """Test get recent alerts"""
    generator = AlertGenerator()

    for i in range(10):
        generator.generate(
            level=AlertLevel.INFO,
            message=f"Test {i}",
            data={"index": i},
            risk_type="test",
        )

    recent = generator.get_recent_alerts(5)
    assert len(recent) == 5
    # Last 5 are the most recent
    assert "Test 9" in recent[-1].message


def test_alert_handler_registration():
    """Test handler registration"""
    generator = AlertGenerator()

    called = False
    captured_alert = None

    def handler(alert):
        nonlocal called, captured_alert
        called = True
        captured_alert = alert

    generator.register_handler(AlertLevel.CRITICAL, handler)

    generator.generate(
        level=AlertLevel.CRITICAL,
        message="Critical test",
        data={},
        risk_type="test",
    )

    assert called is True
    assert captured_alert is not None
    assert captured_alert.message == "Critical test"


def test_alert_to_dict():
    """Test alert serialization"""
    generator = AlertGenerator()
    alert = generator.generate(
        level=AlertLevel.WARNING,
        message="Test message",
        data={"ts_code": "000001.SZ", "value": 100},
        risk_type="position_risk",
    )

    data = alert.to_dict()
    assert data["level"] == "warning"
    assert data["message"] == "Test message"
    assert data["risk_type"] == "position_risk"
    assert data["data"]["ts_code"] == "000001.SZ"


def test_realtime_scanner_init():
    """Test scanner initialization"""
    rule_manager = RuleManager()
    executor = RuleExecutor(rule_manager)
    generator = AlertGenerator()

    scanner = RealtimeRiskScanner(executor, generator, scan_interval_seconds=1)

    assert scanner.is_running() is False
    stats = scanner.get_statistics()
    assert stats["running"] is False


def test_realtime_scanner_callbacks():
    """Test callback registration"""
    rule_manager = RuleManager()
    executor = RuleExecutor(rule_manager)
    generator = AlertGenerator()
    scanner = RealtimeRiskScanner(executor, generator)

    def callback():
        return []

    scanner.register_recent_trades_callback(callback)
    scanner.register_all_positions_callback(callback)

    # Just check registration doesn't crash
    assert True


def test_health_check():
    """Test health check"""
    rule_manager = RuleManager()
    executor = RuleExecutor(rule_manager)
    generator = AlertGenerator()
    scanner = RealtimeRiskScanner(executor, generator)

    health = generator.health_check()
    assert health["status"] == "ok"

    health_scanner = scanner.health_check()
    assert health_scanner["status"] == "stopped"
