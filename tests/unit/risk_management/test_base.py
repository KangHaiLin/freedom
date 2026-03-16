"""
Unit tests for base classes
"""
import pytest
from datetime import datetime
from src.risk_management.base.base_rule import BaseRule, RuleLevel, RuleType
from src.risk_management.base.base_violation import BaseViolation, ViolationLevel


class TestRule(BaseRule):
    """Test concrete rule"""

    def check(self, context):
        value = context.get('value', 0)
        return value <= 100

    def get_violation_message(self, context):
        return f"Value {context.get('value')} exceeds 100"

    def get_violation_details(self, context):
        return {'value': context.get('value'), 'limit': 100}


def test_base_rule_init():
    """Test base rule initialization"""
    rule = TestRule(
        rule_id="test-001",
        rule_name="Test Rule",
        rule_group="pre_trade",
        level=RuleLevel.WARNING,
        enabled=True,
        priority=1,
        description="Test rule description",
    )

    assert rule.rule_id == "test-001"
    assert rule.rule_name == "Test Rule"
    assert rule.rule_group == "pre_trade"
    assert rule.level == RuleLevel.WARNING
    assert rule.enabled is True
    assert rule.priority == 1
    assert "Test rule" in rule.description


def test_base_rule_enable_disable():
    """Test enable/disable methods"""
    rule = TestRule(
        rule_id="test-001",
        rule_name="Test Rule",
        rule_group="pre_trade",
    )

    assert rule.is_enabled() is True
    rule.disable()
    assert rule.is_enabled() is False
    rule.enable()
    assert rule.is_enabled() is True


def test_base_rule_check():
    """Test check method"""
    rule = TestRule(
        rule_id="test-001",
        rule_name="Test Rule",
        rule_group="pre_trade",
    )

    assert rule.check({'value': 50}) is True
    assert rule.check({'value': 150}) is False


def test_base_rule_to_dict():
    """Test serialization"""
    rule = TestRule(
        rule_id="test-001",
        rule_name="Test Rule",
        rule_group="pre_trade",
        level=RuleLevel.ERROR,
        description="Test",
    )

    data = rule.to_dict()

    assert data['rule_id'] == "test-001"
    assert data['rule_name'] == "Test Rule"
    assert data['level'] == "error"
    assert data['description'] == "Test"


def test_base_violation_init():
    """Test base violation initialization"""
    violation = BaseViolation(
        rule_id="test-001",
        rule_name="Test Rule",
        level=ViolationLevel.ERROR,
        message="Test violation",
        details={'key': 'value'},
    )

    assert violation.rule_id == "test-001"
    assert violation.level == ViolationLevel.ERROR
    assert violation.message == "Test violation"
    assert violation.details == {'key': 'value'}


def test_base_violation_is_blocking():
    """Test is_blocking method"""
    assert not BaseViolation("r1", "n", ViolationLevel.INFO, "m", {}).is_blocking()
    assert not BaseViolation("r1", "n", ViolationLevel.WARNING, "m", {}).is_blocking()
    assert BaseViolation("r1", "n", ViolationLevel.ERROR, "m", {}).is_blocking()
    assert BaseViolation("r1", "n", ViolationLevel.CRITICAL, "m", {}).is_blocking()


def test_base_violation_to_dict():
    """Test serialization"""
    violation = BaseViolation(
        rule_id="test-001",
        rule_name="Test Rule",
        level=ViolationLevel.WARNING,
        message="Test message",
        details={'current': 150, 'limit': 100},
    )

    data = violation.to_dict()

    assert data['rule_id'] == "test-001"
    assert data['level'] == "warning"
    assert data['message'] == "Test message"
    assert 'current' in data['details']
