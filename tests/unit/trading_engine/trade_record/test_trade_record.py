"""
Unit tests for trade_record.py
"""
import pytest
from datetime import datetime
from src.trading_engine.trade_record.trade_record import TradeRecord
from src.trading_engine.base.base_order import OrderSide


def test_init():
    """测试初始化"""
    dt = datetime.now()
    record = TradeRecord(
        trade_id='test_1',
        order_id='order_1',
        ts_code='000001.SZ',
        side=OrderSide.BUY,
        filled_quantity=1000,
        filled_price=10.0,
        filled_time=dt,
    )
    assert record.trade_id == 'test_1'
    assert record.order_id == 'order_1'
    assert record.ts_code == '000001.SZ'
    assert record.side == OrderSide.BUY
    assert record.filled_quantity == 1000
    assert record.filled_price == 10.0
    assert record.filled_time == dt


def test_turnover():
    """测试成交额计算"""
    dt = datetime.now()
    record = TradeRecord(
        trade_id='test_1',
        order_id='order_1',
        ts_code='000001.SZ',
        side=OrderSide.BUY,
        filled_quantity=1000,
        filled_price=10.0,
        filled_time=dt,
        commission=5.0,
    )
    assert record.turnover == 10000.0
    assert record.net_turnover == 10000 + 5.0  # 买入佣金增加支出


def test_net_turnover_sell():
    """测试卖出净成交额"""
    dt = datetime.now()
    record = TradeRecord(
        trade_id='test_1',
        order_id='order_1',
        ts_code='000001.SZ',
        side=OrderSide.SELL,
        filled_quantity=1000,
        filled_price=10.0,
        filled_time=dt,
        commission=5.0,
    )
    assert record.turnover == 10000.0
    assert record.net_turnover == 10000 - 5.0  # 卖出佣金减少收入


def test_is_buy_sell():
    """测试买卖判断"""
    dt = datetime.now()
    buy_record = TradeRecord(
        trade_id='test_1',
        order_id='order_1',
        ts_code='000001.SZ',
        side=OrderSide.BUY,
        filled_quantity=1000,
        filled_price=10.0,
        filled_time=dt,
    )
    sell_record = TradeRecord(
        trade_id='test_2',
        order_id='order_2',
        ts_code='000002.SZ',
        side=OrderSide.SELL,
        filled_quantity=500,
        filled_price=20.0,
        filled_time=dt,
    )
    assert buy_record.is_buy
    assert not buy_record.is_sell
    assert not sell_record.is_buy
    assert sell_record.is_sell


def test_to_dict():
    """测试转换为字典"""
    dt = datetime.now()
    record = TradeRecord(
        trade_id='test_1',
        order_id='order_1',
        ts_code='000001.SZ',
        side=OrderSide.BUY,
        filled_quantity=1000,
        filled_price=10.0,
        filled_time=dt,
        commission=5.0,
        pnl=None,
    )
    d = record.to_dict()
    assert d['trade_id'] == 'test_1'
    assert d['order_id'] == 'order_1'
    assert d['ts_code'] == '000001.SZ'
    assert d['side'] == 'BUY'
    assert d['filled_quantity'] == 1000
    assert d['filled_price'] == 10.0
    assert 'filled_time' in d
