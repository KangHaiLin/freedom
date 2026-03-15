"""
Unit tests for pre_trade_check.py
"""
import pytest
from src.trading_engine.risk_control.pre_trade_check import PreTradeChecker, PreTradeCheckResult
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.base.base_order import OrderSide


def test_pass_when_normal():
    """测试正常情况通过"""
    pm = PortfolioManager(100000.0)
    checker = PreTradeChecker(
        max_position_value=0.1,
        max_concentration=10,
        min_cash_reserve=0.05,
    )
    # 买入1000*10 = 10000，占总资产10%，正好
    result = checker.check_order('000001.SZ', OrderSide.BUY, 1000, 10.0, pm)
    assert result.passed


def test_fail_max_count():
    """测试超出最大持仓数量"""
    pm = PortfolioManager(100000.0)
    # 已经10只，再买一只不行
    for i in range(10):
        pm.add_position(f'{i:06d}.SZ', 100, 10.0)
    checker = PreTradeChecker(max_concentration=10)
    result = checker.check_order('999999.SZ', OrderSide.BUY, 100, 10.0, pm)
    assert not result.passed
    assert '超出最大持仓数量' in result.message


def test_fail_single_position_too_large():
    """测试单票太大"""
    pm = PortfolioManager(100000.0)
    checker = PreTradeChecker(max_position_value=0.1)
    # 买入2000*10=20000，占20% > 10%
    result = checker.check_order('000001.SZ', OrderSide.BUY, 2000, 10.0, pm)
    assert not result.passed
    assert '单票市值超出限制' in result.message


def test_fail_insufficient_cash():
    """测试资金不足"""
    pm = PortfolioManager(10000.0)
    checker = PreTradeChecker(max_position_value=0.95, min_cash_reserve=0.05)
    # 几乎买完，预留不足
    result = checker.check_order('000001.SZ', OrderSide.BUY, 1000, 9.5, pm)
    # 需要 9500 * 1.001 = 9509.5，剩余 10000 - 9509.5 = 490.5
    # 需要预留 10000 * 0.05 = 500，不够
    assert not result.passed
    assert '现金不足' in result.message


def test_fail_insufficient_position_sell():
    """测试卖出持仓不足"""
    pm = PortfolioManager(100000.0)
    pm.add_position('000001.SZ', 500, 10.0)
    checker = PreTradeChecker()
    result = checker.check_order('000001.SZ', OrderSide.SELL, 1000, 10.0, pm)
    assert not result.passed
    assert '持仓不足' in result.message


def test_pass_sell():
    """测试卖出正常通过"""
    pm = PortfolioManager(100000.0)
    pm.add_position('000001.SZ', 1000, 10.0)
    checker = PreTradeChecker()
    result = checker.check_order('000001.SZ', OrderSide.SELL, 500, 12.0, pm)
    assert result.passed
