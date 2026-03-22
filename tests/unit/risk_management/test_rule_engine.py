"""
Unit tests for rule engine
"""

import pytest

from src.risk_management.base.base_rule import RuleLevel
from src.risk_management.rule_engine.builtins import (
    create_insufficient_cash_rule,
    create_single_position_concentration_rule,
    get_default_pre_trade_rules,
)
from src.risk_management.rule_engine.rule import Rule, RuleVersion
from src.risk_management.rule_engine.rule_executor import RuleExecutor
from src.risk_management.rule_engine.rule_manager import RuleManager
from src.risk_management.rule_engine.rule_result import RuleResult, RuleViolation


def test_rule_init():
    """Test rule creation"""

    def check(ctx):
        return ctx.get("value", 0) <= 100

    def message(ctx):
        return f"Value {ctx.get('value')} > 100"

    def details(ctx):
        return {"value": ctx.get("value"), "limit": 100}

    rule = Rule(
        rule_id="test-001",
        rule_name="Value Limit",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=RuleLevel.BLOCK,
        description="Test value limit",
    )

    assert rule.rule_id == "test-001"
    assert rule.check({"value": 50}) is True
    assert rule.check({"value": 150}) is False
    assert "Value 150" in rule.get_violation_message({"value": 150})
    assert rule.get_violation_details({"value": 150})["value"] == 150


def test_rule_result():
    """Test RuleResult"""
    from src.risk_management.base.base_violation import ViolationLevel

    result = RuleResult()
    assert result.passed() is True

    violation = RuleViolation(
        rule_id="test-001",
        rule_name="Test",
        level=ViolationLevel.WARNING,
        message="Test warning",
        details={},
    )
    result.add_violation(violation)

    assert result.has_violations() is True
    assert len(result.get_violations()) == 1
    # WARNING is not blocking
    assert result.passed() is True

    # Add blocking violation
    violation2 = RuleViolation(
        rule_id="test-002",
        rule_name="Test2",
        level=ViolationLevel.ERROR,
        message="Test error",
        details={},
    )
    result.add_violation(violation2)

    assert result.passed() is False


def test_rule_manager():
    """Test RuleManager"""
    manager = RuleManager()

    def check(ctx):
        return ctx.get("value", 0) <= 100

    def message(ctx):
        return f"Value {ctx.get('value')} > 100"

    rule = Rule(
        rule_id="test-001",
        rule_name="Test",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
    )

    version = manager.add_rule(rule, created_by=1)
    assert version.version_id is not None

    # Get rule
    stored = manager.get_rule("test-001")
    assert stored is not None

    # Get by group
    rules = manager.get_rules_by_group("pre_trade")
    assert len(rules) == 1

    # Count
    stats = manager.count_rules()
    assert stats["total"] == 1
    assert stats["enabled"] == 1

    # Disable
    manager.disable_rule("test-001")
    stats = manager.count_rules()
    assert stats["enabled"] == 0

    # Delete
    assert manager.delete_rule("test-001") is True
    assert manager.get_rule("test-001") is None


def test_rule_executor():
    """Test RuleExecutor"""
    manager = RuleManager()
    executor = RuleExecutor(manager)

    # Add test rule: value <= 100
    rule = create_single_position_concentration_rule(max_ratio=0.3)
    manager.add_rule(rule, created_by=1)

    # Check within limit
    result = executor.execute(
        "pre_trade",
        {
            "total_asset": 100000,
            "current_quantity": 0,
            "price": 10,
            "quantity": 2000,
        },
    )
    # 2000 * 10 / 100000 = 0.2 < 0.3 -> pass
    assert result.passed() is True

    # Check over limit
    result = executor.execute(
        "pre_trade",
        {
            "total_asset": 100000,
            "current_quantity": 0,
            "price": 10,
            "quantity": 4000,
        },
    )
    # 4000 * 10 / 100000 = 0.4 > 0.3 -> fail
    assert result.passed() is False
    assert len(result.get_violations()) == 1
    assert "持仓比例超限" in result.get_violations()[0].message


def test_builtin_insufficient_cash():
    """Test insufficient cash rule"""
    rule = create_insufficient_cash_rule()
    assert rule.check({"available_cash": 10000, "required_amount": 5000}) is True
    assert rule.check({"available_cash": 10000, "required_amount": 15000}) is False
    assert "可用资金不足" in rule.get_violation_message({})


def test_builtin_default_rules():
    """Test get default rules"""
    rules = get_default_pre_trade_rules()
    assert len(rules) > 0
    for rule in rules:
        assert rule.rule_id is not None
        assert rule.check is not None


def test_rule_version_gray():
    """Test gray version matching"""
    version = RuleVersion(
        version_id="v1",
        rule_id="test",
        rule_content="",
        rule_group="pre_trade",
        created_by=1,
        gray_percentage=50,
        gray_users=[1, 2, 3],
    )

    assert version.is_gray() is True
    assert version.matches_user(2) is True
    # User 4 doesn't hit list, depends on hash
    # Can't predict exact result but shouldn't crash
    result = version.matches_user(4)
    assert isinstance(result, bool)


def test_single_position_concentration_correctness():
    """Test single position concentration calculation"""
    rule = create_single_position_concentration_rule(max_ratio=0.3)

    # Empty current position, buying 30%
    ctx = {
        "total_asset": 100000,
        "current_quantity": 0,
        "price": 30,
        "quantity": 1000,  # 30 * 1000 = 30000 -> 30%
    }
    assert rule.check(ctx) is True

    # Buying 31%
    ctx = {
        "total_asset": 100000,
        "current_quantity": 0,
        "price": 31,
        "quantity": 1000,  # 31000 -> 31%
    }
    assert rule.check(ctx) is False
    details = rule.get_violation_details(ctx)
    assert abs(details["current_ratio"] - 0.31) < 0.0001
