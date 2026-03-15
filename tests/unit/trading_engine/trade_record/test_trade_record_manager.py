"""
Unit tests for trade_record_manager.py
"""
import pytest
from datetime import datetime, timedelta
from src.trading_engine.trade_record.trade_record_manager import TradeRecordManager
from src.trading_engine.order_management.order import Order
from src.trading_engine.base.base_order import OrderSide


def test_init():
    """测试初始化"""
    manager = TradeRecordManager()
    assert manager.get_trade_count() == 0


def test_add_record():
    """测试添加记录"""
    manager = TradeRecordManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    dt = datetime.now()
    record = manager.add_record(order, 1000, 10.0, dt, 5.0, 0.0)
    assert record is not None
    assert record.trade_id is not None
    assert manager.get_trade_count() == 1


def test_get_record():
    """测试获取记录"""
    manager = TradeRecordManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    dt = datetime.now()
    record = manager.add_record(order, 1000, 10.0, dt)
    got = manager.get_record(record.trade_id)
    assert got is record


def test_get_trades_by_order():
    """测试获取订单的所有成交"""
    manager = TradeRecordManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    dt = datetime.now()
    # 分两次成交
    manager.add_record(order, 500, 10.0, dt)
    manager.add_record(order, 500, 10.1, dt + timedelta(minutes=1))
    trades = manager.get_trades_by_order(order.order_id)
    assert len(trades) == 2


def test_query_by_ts_code():
    """测试按股票代码查询"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt)
    manager.add_record(order2, 500, 20.0, dt)
    result = manager.query_records(ts_code='000001.SZ')
    assert len(result) == 1
    assert result[0].ts_code == '000001.SZ'


def test_query_by_strategy_id():
    """测试按策略ID查询"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000, strategy_id='strategy1')
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 500, strategy_id='strategy2')
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt)
    manager.add_record(order2, 500, 20.0, dt)
    result = manager.query_records(strategy_id='strategy1')
    assert len(result) == 1
    assert result[0].strategy_id == 'strategy1'


def test_query_by_side():
    """测试按买卖方向查询"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.SELL, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt)
    manager.add_record(order2, 500, 20.0, dt)
    result = manager.query_records(side=OrderSide.BUY)
    assert len(result) == 1
    assert result[0].side == OrderSide.BUY


def test_get_total_turnover():
    """测试计算总成交额"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.SELL, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt, 5.0)
    manager.add_record(order2, 500, 20.0, dt, 5.0)
    # 1000*10 + 500*20 = 10000 + 10000 = 20000
    assert abs(manager.get_total_turnover() - 20000) < 0.01


def test_get_total_commission():
    """测试计算总佣金"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.SELL, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt, 5.0)
    manager.add_record(order2, 500, 20.0, dt, 5.0)
    assert abs(manager.get_total_commission() - 10.0) < 0.01


def test_get_realized_pnl_total():
    """测试计算总实现盈亏"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.SELL, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.SELL, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 12.0, dt, pnl=2000)
    manager.add_record(order2, 500, 18.0, dt, pnl=-500)
    # 2000 - 500 = 1500
    assert abs(manager.get_realized_pnl_total() - 1500) < 0.01


def test_get_statistics():
    """测试获取统计信息"""
    manager = TradeRecordManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.SELL, 500)
    dt = datetime.now()
    manager.add_record(order1, 1000, 10.0, dt)
    manager.add_record(order2, 500, 20.0, dt)
    stats = manager.get_statistics()
    assert stats['total_trades'] == 2
    assert stats['buy_trades'] == 1
    assert stats['sell_trades'] == 1
    assert stats['total_turnover'] == 1000*10 + 500*20


def test_clear_all():
    """测试清空"""
    manager = TradeRecordManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    dt = datetime.now()
    manager.add_record(order, 1000, 10.0, dt)
    assert manager.get_trade_count() == 1
    manager.clear_all()
    assert manager.get_trade_count() == 0
