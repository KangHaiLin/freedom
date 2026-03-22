"""
Unit tests for risk_controller.py
"""

import pytest

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.risk_control.pre_trade_check import PreTradeChecker
from src.trading_engine.risk_control.risk_controller import RiskController


def test_pass_all():
    """测试全部通过"""
    pm = PortfolioManager(100000.0)
    rc = RiskController()
    result = rc.check_order(
        "000001.SZ",
        OrderSide.BUY,
        1000,
        10.0,
        pm,
    )
    assert result.passed
    assert result.pre_trade_passed
    assert result.compliance_passed


def test_fail_pre_trade():
    """测试事前风控失败"""
    pm = PortfolioManager(100000.0)
    for i in range(10):
        pm.add_position(f"{i:06d}.SZ", 100, 10.0)
    rc = RiskController()
    result = rc.check_order(
        "999999.SZ",
        OrderSide.BUY,
        100,
        10.0,
        pm,
    )
    assert not result.passed
    assert not result.pre_trade_passed
    assert result.compliance_passed is None


def test_fail_compliance():
    """测试合规失败"""
    pm = PortfolioManager(100000.0)
    # 自定义更大单票限制，让pre_trade通过
    pre_trade = PreTradeChecker(max_position_value=0.2)
    rc = RiskController(pre_trade)
    result = rc.check_order(
        "000001.SZ",
        OrderSide.BUY,
        1000,
        11.1,
        pm,
        limit_up=11.0,
        limit_down=9.0,
    )
    assert not result.passed
    assert result.pre_trade_passed
    assert not result.compliance_passed


def test_check_portfolio_risk_alert():
    """测试投资组合回撤警示"""
    pm = PortfolioManager(100000.0)
    rc = RiskController()
    # 现在没有亏损，不会警示
    result = rc.check_portfolio_risk(pm, max_drawdown=0.2)
    assert not result["alert"]


def test_get_checkers():
    """测试获取检查器"""
    rc = RiskController()
    assert rc.get_pre_trade_checker() is not None
    assert rc.get_compliance_rules() is not None


def test_health_check():
    """测试健康检查"""
    rc = RiskController()
    health = rc.health_check()
    assert health["status"] == "ok"
