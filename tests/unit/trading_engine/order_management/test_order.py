"""
Unit tests for order.py
"""

from datetime import datetime

import pytest

from src.trading_engine.base.base_order import OrderSide, OrderStatus, OrderType
from src.trading_engine.order_management.order import Order


def test_create_market_order():
    """测试创建市价单"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000, strategy_id="test_1")
    assert order.ts_code == "000001.SZ"
    assert order.side == OrderSide.BUY
    assert order.quantity == 1000
    assert order.order_type == OrderType.MARKET
    assert order.order_id is not None
    assert len(order.order_id) == 8
    assert order.strategy_id == "test_1"


def test_create_limit_order():
    """测试创建限价单"""
    order = Order.create_limit_order("000001.SZ", OrderSide.BUY, 1000, 10.5)
    assert order.order_type == OrderType.LIMIT
    assert order.price == 10.5


def test_create_stop_order():
    """测试创建止损单"""
    order = Order.create_stop_order("000001.SZ", OrderSide.SELL, 1000, 10.0)
    assert order.order_type == OrderType.STOP
    assert order.stop_price == 10.0


def test_create_stop_limit_order():
    """测试创建止损限价单"""
    order = Order.create_stop_limit_order("000001.SZ", OrderSide.SELL, 1000, 10.0, 9.8)
    assert order.order_type == OrderType.STOP_LIMIT
    assert order.stop_price == 10.0
    assert order.price == 9.8


def test_is_buy_sell():
    """测试买卖方向判断"""
    buy_order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    sell_order = Order.create_market_order("000001.SZ", OrderSide.SELL, 1000)
    assert buy_order.is_buy()
    assert not buy_order.is_sell()
    assert not sell_order.is_buy()
    assert sell_order.is_sell()


def test_get_remaining_quantity():
    """测试获取剩余数量"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    assert order.get_remaining_quantity() == 1000
    order.fill(300, 10.0, datetime.now())
    assert order.get_remaining_quantity() == 700


def test_full_fill():
    """测试完全成交"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    assert not order.is_filled()
    order.fill(1000, 10.0, datetime.now())
    assert order.is_filled()
    assert order.filled_avg_price == 10.0
    assert order.filled_at is not None


def test_partial_fill():
    """测试部分成交"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    order.fill(400, 10.0, datetime.now())
    assert order.is_partial_filled()
    assert not order.is_filled()
    assert order.filled_quantity == 400


def test_average_price_calculation():
    """测试平均价格计算"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    order.fill(500, 10.0, datetime.now())
    order.fill(500, 11.0, datetime.now())
    # (500*10 + 500*11) / 1000 = 10.5
    assert order.filled_avg_price == 10.5


def test_can_cancel():
    """测试可取消判断"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    assert order.can_cancel()  # PENDING
    order.submit()
    assert order.can_cancel()  # SUBMITTED
    order.fill(500, 10.0, datetime.now())
    assert order.can_cancel()  # PARTIAL
    order.fill(500, 10.0, datetime.now())
    assert not order.can_cancel()  # FILLED


def test_status_transitions():
    """测试状态转换"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    assert order.status == OrderStatus.PENDING

    order.submit()
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None

    order.cancel()
    assert order.status == OrderStatus.CANCELLED

    order.reject()
    assert order.status == OrderStatus.REJECTED


def test_can_trigger_stop_buy():
    """测试买入止损触发条件"""
    order = Order.create_stop_order("000001.SZ", OrderSide.BUY, 1000, 10.5)
    assert not order.can_trigger(10.0)
    assert order.can_trigger(11.0)


def test_can_trigger_stop_sell():
    """测试卖出止损触发条件"""
    order = Order.create_stop_order("000001.SZ", OrderSide.SELL, 1000, 10.0)
    assert not order.can_trigger(10.5)
    assert order.can_trigger(9.5)


def test_get_notional():
    """测试名义价值计算"""
    order = Order.create_limit_order("000001.SZ", OrderSide.BUY, 1000, 10.0)
    assert order.get_notional() == 10000.0


def test_get_filled_notional():
    """测试成交名义价值计算"""
    order = Order.create_limit_order("000001.SZ", OrderSide.BUY, 1000, 10.0)
    order.fill(500, 10.0, datetime.now())
    assert order.get_filled_notional() == 5000.0


def test_to_dict():
    """测试转换为字典"""
    order = Order.create_market_order("000001.SZ", OrderSide.BUY, 1000)
    d = order.to_dict()
    assert d["order_id"] == order.order_id
    assert d["ts_code"] == "000001.SZ"
    assert d["side"] == "BUY"
    assert d["quantity"] == 1000
    assert d["filled_quantity"] == 0
    assert d["order_type"] == "MARKET"
    assert d["status"] == "PENDING"
