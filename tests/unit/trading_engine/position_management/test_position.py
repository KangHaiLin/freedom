"""
Unit tests for position.py
"""

import pytest

from src.trading_engine.position_management.position import Position


def test_init():
    """测试初始化"""
    pos = Position("000001.SZ", 1000, 10.0)
    assert pos.ts_code == "000001.SZ"
    assert pos.quantity == 1000
    assert pos.avg_cost == 10.0
    assert not pos.is_empty()


def test_empty_position():
    """测试空持仓"""
    pos = Position("000001.SZ", 0, 0.0)
    assert pos.is_empty()
    assert pos.get_market_value() == 0.0


def test_update_price():
    """测试更新价格"""
    pos = Position("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    assert pos.last_price == 12.0
    assert pos.last_update_time is not None


def test_get_market_value():
    """测试市值计算"""
    pos = Position("000001.SZ", 1000, 10.0)
    assert pos.get_market_value() == 0.0
    pos.update_price(12.0)
    assert pos.get_market_value() == 12000.0


def test_get_unrealized_pnl():
    """测试未实现盈亏"""
    pos = Position("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    assert pos.get_unrealized_pnl() == 2000.0


def test_get_unrealized_pnl_pct():
    """测试未实现盈亏百分比"""
    pos = Position("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    assert pos.get_unrealized_pnl_pct() == 0.2


def test_add_position():
    """测试增加持仓"""
    pos = Position("000001.SZ", 1000, 10.0)
    new_avg = pos.add_position(500, 11.0, 5.0)
    # (1000*10 + 500*11 + 5) / 1500 = (10000 + 5500 + 5)/1500 = 15505/1500 ≈ 10.3367
    assert pos.quantity == 1500
    assert abs(new_avg - 10.3367) < 0.001
    assert pos.total_bought == 500


def test_reduce_position():
    """测试减少持仓"""
    pos = Position("000001.SZ", 1000, 10.0)
    pnl = pos.reduce_position(500, 12.0, 5.0)
    # (12 - 10)*500 - 5 = 1000 - 5 = 995
    assert abs(pnl - 995) < 0.001
    assert pos.quantity == 500
    assert pos.realized_pnl == 995


def test_close_position():
    """测试平仓"""
    pos = Position("000001.SZ", 1000, 10.0)
    pnl = pos.close_position(12.0, 5.0)
    # (12 - 10)*1000 - 5 = 2000 - 5 = 1995
    assert abs(pnl - 1995) < 0.001
    assert pos.is_empty()
    assert pos.realized_pnl == 1995


def test_to_dict():
    """测试转换为字典"""
    pos = Position("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    d = pos.to_dict()
    assert d["ts_code"] == "000001.SZ"
    assert d["quantity"] == 1000
    assert d["avg_cost"] == 10.0
    assert d["last_price"] == 12.0
    assert d["market_value"] == 12000.0
    assert d["unrealized_pnl"] == 2000.0
