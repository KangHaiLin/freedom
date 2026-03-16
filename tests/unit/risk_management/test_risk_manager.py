"""
Unit tests for unified RiskManager
"""
import pytest
from datetime import date
from src.risk_management.risk_manager import RiskManager
from src.risk_management.rule_engine.rule import Rule
from src.risk_management.base.base_rule import RuleLevel


def test_init():
    """Test RiskManager initialization"""
    rm = RiskManager(load_default_rules=True)
    health = rm.health_check()

    assert health['status'] == 'ok'
    assert 'rule_engine' in health
    assert 'stats' in health
    # Should have loaded default rules
    assert health['stats']['total_rules'] > 0


def test_pre_trade_check_pass():
    """Test pre-trade check that passes"""
    rm = RiskManager(load_default_rules=True)

    result = rm.pre_trade_check(
        user_id=1,
        ts_code='000001.SZ',
        side='BUY',
        price=10.0,
        quantity=1000,
        available_cash=20000,
        required_amount=10000,
        total_asset=100000,
        current_position_count=5,
    )

    assert result.passed() is True
    assert not result.has_violations()


def test_pre_trade_check_fail_insufficient_cash():
    """Test pre-trade check fails on insufficient cash"""
    rm = RiskManager(load_default_rules=True)

    result = rm.pre_trade_check(
        user_id=1,
        ts_code='000001.SZ',
        side='BUY',
        price=10.0,
        quantity=10000,
        available_cash=50000,
        required_amount=100000,
        total_asset=100000,
    )

    assert result.passed() is False
    assert '可用资金不足' in result.get_violations()[0].message


def test_pre_trade_check_fail_concentration():
    """Test pre-trade check fails on concentration"""
    rm = RiskManager(load_default_rules=True)

    # 买入30% is okay, but 40% exceeds default 30% limit
    result = rm.pre_trade_check(
        user_id=1,
        ts_code='000001.SZ',
        side='BUY',
        price=10.0,
        quantity=4000,
        available_cash=100000,
        required_amount=40000,
        total_asset=100000,
        current_quantity=0,
    )

    assert result.passed() is False
    assert any('持仓比例超限' in v.message for v in result.get_violations())


def test_add_rule():
    """Test adding custom rule"""
    rm = RiskManager(load_default_rules=False)

    def check(ctx):
        return ctx.get('value', 0) <= 100

    def message(ctx):
        return f'Value {ctx.get("value")} exceeds 100'

    rule = Rule(
            rule_id='custom-001',
            rule_name='Custom Value Limit',
            rule_group='pre_trade',
            check_func=check,
            message_func=message,
            level=RuleLevel.WARNING,
        )

    version = rm.add_rule(rule, created_by=1)
    assert version.version_id is not None

    stored = rm.get_rule('custom-001')
    assert stored is not None
    assert stored.rule_name == 'Custom Value Limit'


def test_enable_disable_rule():
    """Test enable/disable rule"""
    rm = RiskManager(load_default_rules=False)

    def check(ctx):
        return ctx.get('value', 0) <= 100

    def message(ctx):
        return f'Value {ctx.get("value")} exceeds 100'

    rule = Rule(
            rule_id='test-001',
            rule_name='Test',
            rule_group='pre_trade',
            check_func=check,
            message_func=message,
        )
    rm.add_rule(rule, created_by=1)

    assert rm.get_rule('test-001').is_enabled() is True

    result = rm.disable_rule('test-001', operator_id=1)
    assert result is True
    assert rm.get_rule('test-001').is_enabled() is False

    result = rm.enable_rule('test-001', operator_id=1)
    assert result is True
    assert rm.get_rule('test-001').is_enabled() is True


def test_list_all_rules():
    """Test listing all rules"""
    rm = RiskManager(load_default_rules=True)
    rules = rm.list_all_rules()
    assert len(rules) > 0


def test_compliance_check_t1():
    """Test T+1 compliance check through manager"""
    rm = RiskManager()
    result = rm.compliance_check_t1(
        available_quantity=1000, sell_quantity=500, today_bought=300)
    assert result['passed'] is True

    result = rm.compliance_check_t1(
        available_quantity=1000, sell_quantity=800, today_bought=300)
    assert result['passed'] is False


def test_compliance_check_price_limit():
    """Test price limit check through manager"""
    rm = RiskManager()
    result = rm.compliance_check_price_limit(10.5, 11.0, 9.0)
    assert result['passed'] is True

    result = rm.compliance_check_price_limit(11.5, 11.0, 9.0)
    assert result['passed'] is False


def test_calculate_var():
    """Test VaR calculation through manager"""
    import pandas as pd
    import numpy as np
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 1000))

    rm = RiskManager()
    result = rm.calculate_var(returns, 100000, method='historical')

    assert 'var' in result
    assert result['var'] > 0
    assert result['method'] == 'historical'


def test_run_stress_test():
    """Test stress test through manager"""
    rm = RiskManager()

    positions = {
        '000001.SZ': {'quantity': 1000, 'last_price': 10},
        '600000.SH': {'quantity': 500, 'last_price': 20},
    }

    result = rm.run_stress_test('systemic_down_10', positions)

    assert result['success'] is True
    assert result['total_pnl'] < 0
    assert result['total_pnl_pct'] < 0


def test_check_limit():
    """Test limit check through manager"""
    rm = RiskManager()
    result = rm.check_limit('single_position_ratio', 0.25)
    # Default limit is 0.3, so 0.25 passes
    assert result['passed'] is True

    result = rm.check_limit('single_position_ratio', 0.35)
    assert result['passed'] is False


def test_query_risk_events():
    """Test querying risk events"""
    rm = RiskManager()
    events = rm.query_risk_events()
    # Initially empty unless events
    assert isinstance(events, list)


def test_get_risk_statistics():
    """Test getting risk statistics"""
    rm = RiskManager()
    stats = rm.get_risk_statistics()
    assert 'total_events' in stats
    assert 'unhandled' in stats


def test_health_check():
    """Test full health check"""
    rm = RiskManager()
    health = rm.health_check()

    assert health['status'] == 'ok'
    assert 'rule_engine' in health
    assert 'alert_generator' in health
    assert 'compliance_checker' in health
    assert 'limit_manager' in health
    assert 'operation_logger' in health
    assert 'risk_event_store' in health
    assert 'stats' in health


def test_reset_daily_limits():
    """Test reset daily limits"""
    rm = RiskManager()
    rm.reset_daily_limits()
    # Just check it doesn't crash
    assert True
