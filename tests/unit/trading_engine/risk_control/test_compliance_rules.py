"""
Unit tests for compliance_rules.py
"""

import pytest

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.risk_control.compliance_rules import AShareComplianceRules


def test_pass_normal_buy():
    """测试正常买入通过"""
    pm = PortfolioManager(100000.0)
    rules = AShareComplianceRules()
    result = rules.check_order("000001.SZ", OrderSide.BUY, 1000, 10.0, pm)
    assert result.compliant


def test_fail_buy_delisted():
    """测试不能买入退市"""
    pm = PortfolioManager(100000.0)
    rules = AShareComplianceRules()
    result = rules.check_order("000001.SZ", OrderSide.BUY, 1000, 10.0, pm, is_delisted=True)
    assert not result.compliant
    assert "退市" in result.message


def test_fail_trade_suspended():
    """测试不能交易停牌"""
    pm = PortfolioManager(100000.0)
    rules = AShareComplianceRules()
    result = rules.check_order("000001.SZ", OrderSide.BUY, 1000, 10.0, pm, is_suspended=True)
    assert not result.compliant
    assert "停牌" in result.message


def test_t1_block_sell():
    """测试T+1禁止当日买入当日卖出"""
    pm = PortfolioManager(100000.0)
    # 昨日之前没有持仓，今日买入1000，现在要卖出1000
    pm.add_position("000001.SZ", 1000, 10.0)
    today_trades = [{"ts_code": "000001.SZ", "side": OrderSide.BUY, "filled_quantity": 1000}]
    rules = AShareComplianceRules(enable_t1_check=True)
    result = rules.check_order("000001.SZ", OrderSide.SELL, 1000, 12.0, pm, today_trades=today_trades)
    assert not result.compliant
    assert "T+1" in result.message


def test_t1_allowed_sell():
    """测试可以卖出昨日持仓"""
    pm = PortfolioManager(100000.0)
    # 之前就有持仓，不是今日买入
    pm.add_position("000001.SZ", 1000, 10.0)
    today_trades = []
    rules = AShareComplianceRules(enable_t1_check=True)
    result = rules.check_order("000001.SZ", OrderSide.SELL, 500, 12.0, pm, today_trades=today_trades)
    assert result.compliant


def test_price_limit_above_up():
    """测试价格超过涨停不允许"""
    pm = PortfolioManager(100000.0)
    rules = AShareComplianceRules()
    # 涨停11，委托11.1买入
    result = rules.check_order("000001.SZ", OrderSide.BUY, 1000, 11.1, pm, limit_up=11.0, limit_down=9.0)
    assert not result.compliant
    assert "涨停" in result.message


def test_price_limit_below_down():
    """测试价格低于跌停不允许"""
    pm = PortfolioManager(100000.0)
    # 添加昨日持仓，不是今日买入
    pm.add_position("000001.SZ", 1000, 10.0)
    rules = AShareComplianceRules()
    # 跌停9，委托8.9卖出
    result = rules.check_order(
        "000001.SZ", OrderSide.SELL, 1000, 8.9, pm, today_trades=[], limit_up=11.0, limit_down=9.0
    )
    assert not result.compliant
    assert "跌停" in result.message


def test_calculate_limit_price():
    """测试计算涨跌停"""
    up, down = AShareComplianceRules.calculate_limit_price(10.0, 0.10)
    assert up == 11.0
    assert down == 9.0


def test_get_limit_rate():
    """测试获取涨跌停比例"""
    assert AShareComplianceRules.get_limit_rate("000001.SZ") == 0.10
    assert AShareComplianceRules.get_limit_rate("ST0001") == 0.05
    assert AShareComplianceRules.get_limit_rate("*ST0002") == 0.05
