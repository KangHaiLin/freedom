"""
Unit tests for portfolio_manager.py
"""

from datetime import datetime

import pytest

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.order_management.order import Order
from src.trading_engine.position_management.portfolio_manager import PortfolioManager


def test_init():
    """测试初始化"""
    pm = PortfolioManager(initial_cash=100000.0)
    assert pm.get_cash() == 100000.0
    assert pm.get_initial_cash() == 100000.0
    assert pm.get_position_count() == 0


def test_get_or_create_position():
    """测试获取或创建持仓"""
    pm = PortfolioManager(100000.0)
    pos = pm.get_or_create_position("000001.SZ")
    assert pos is not None
    assert pos.ts_code == "000001.SZ"
    assert pm.get_position_count() == 0  # 空持仓不算
    assert pm.get_position("000001.SZ") is pos


def test_add_position():
    """测试增加持仓"""
    pm = PortfolioManager(100000.0)
    new_avg, total_cost = pm.add_position("000001.SZ", 1000, 10.0, 5.0)
    # 总花费 = 1000*10 + 5 = 10005
    assert abs(total_cost - 10005) < 0.01
    assert abs(new_avg - 10.005) < 0.0001
    assert pm.get_cash() == 100000 - 10005
    assert pm.get_position_count() == 1


def test_reduce_position():
    """测试减少持仓"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0, 5.0)
    initial_cash = pm.get_cash()
    pnl, total_amount = pm.reduce_position("000001.SZ", 500, 12.0, 5.0)
    # 总收入 = 500*12 - 5 = 6000 - 5 = 5995
    # 盈亏 = (12 - 10.005)*500 - 5 = 1.995*500 -5 = 997.5 -5 = 992.5
    assert abs(total_amount - 5995) < 0.01
    assert abs(pnl - 992.5) < 0.01
    assert pm.get_cash() == initial_cash + 5995
    pos = pm.get_position("000001.SZ")
    assert pos.quantity == 500


def test_close_position():
    """测试平仓"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0, 5.0)
    initial_cash = pm.get_cash()
    pnl, total_amount = pm.close_position("000001.SZ", 12.0, 5.0)
    # 总收入 = 1000*12 - 5 = 11995
    # 盈亏 = (12 - 10.005)*1000 - 5 = 1995 -5 = 1990
    assert abs(total_amount - 11995) < 0.01
    assert abs(pnl - 1990) < 0.01
    assert pm.get_cash() == initial_cash + 11995
    assert pm.get_position_count() == 0
    pos = pm.get_position("000001.SZ")
    assert pos.quantity == 0


def test_process_order_fill_buy():
    """测试处理买单成交"""
    pm = PortfolioManager(100000.0)
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    result = pm.process_order_fill(order, 1000, 10.0, 5.0)
    assert result == -(1000 * 10 + 5)
    assert pm.get_position_count() == 1
    assert pm.get_cash() == 100000 - 10005


def test_process_order_fill_sell():
    """测试处理卖单成交"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0, 5.0)
    order = Order.create_market_order("000001.SZ", OrderSide.SELL, 500)
    pnl = pm.process_order_fill(order, 500, 12.0, 5.0)
    # 验证盈亏计算正确
    assert pnl > 0


def test_update_prices():
    """测试批量更新价格"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0)
    pm.add_position("000002.SZ", 500, 20.0)
    pm.update_prices(
        {
            "000001.SZ": 12.0,
            "000002.SZ": 18.0,
        }
    )
    pos1 = pm.get_position("000001.SZ")
    pos2 = pm.get_position("000002.SZ")
    assert pos1.last_price == 12.0
    assert pos2.last_price == 18.0


def test_get_summary():
    """测试获取汇总信息"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0)
    pm.add_position("000002.SZ", 500, 20.0)
    pm.update_prices(
        {
            "000001.SZ": 12.0,
            "000002.SZ": 18.0,
        }
    )
    summary = pm.get_summary()
    assert summary["position_count"] == 2
    assert abs(summary["total_market_value"] - 21000) < 0.01
    assert abs(summary["total_unrealized_pnl"] - 1000) < 0.01
    assert abs(summary["total_asset"] - (21000 + (100000 - 1000 * 10 - 500 * 20))) < 0.01


def test_check_buy_available():
    """测试检查买入资金"""
    pm = PortfolioManager(10000.0)
    # 买入1000股，价格10，佣金率0.0003
    # 需要 1000*10*(1+0.0003) = 10003
    assert not pm.check_buy_available(10.0, 1000, 0.0003)  # 需要10003，只有10000
    assert pm.check_buy_available(10.0, 900, 0.0003)  # 需要9002.7，有10000


def test_check_sell_available():
    """测试检查持仓是否足够卖出"""
    pm = PortfolioManager(10000.0)
    pm.add_position("000001.SZ", 1000, 10.0)
    assert pm.check_sell_available("000001.SZ", 500)
    assert pm.check_sell_available("000001.SZ", 1000)
    assert not pm.check_sell_available("000001.SZ", 1500)
    assert not pm.check_sell_available("000002.SZ", 100)


def test_to_dict():
    """测试转换为字典"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0)
    pm.update_price("000001.SZ", 12.0)
    d = pm.to_dict()
    assert d["initial_cash"] == 100000.0
    assert "current_cash" in d
    assert "total_asset" in d
    assert "summary" in d
    assert "positions" in d
    assert d["position_count"] == 1


def test_clear_all():
    """测试清空"""
    pm = PortfolioManager(100000.0)
    pm.add_position("000001.SZ", 1000, 10.0)
    pm.add_position("000002.SZ", 500, 20.0)
    assert pm.get_position_count() == 2
    pm.clear_all()
    assert pm.get_position_count() == 0
