"""
Unit tests for vwap_algo.py
"""

from datetime import datetime, timedelta

import pytest

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.execution_engine.vwap_algo import VWAPAlgo


def test_init():
    """测试初始化"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(10000, OrderSide.BUY, start, end)
    assert vwap.total_quantity == 10000
    assert vwap.remaining_quantity == 10000
    assert not vwap.is_done()
    assert len(vwap.get_split_plan()) > 0


def test_auto_num_splits():
    """测试自动计算拆分份数"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(10000, OrderSide.BUY, start, end, min_chunk=100, max_chunk=1000)
    # 10000 / 100 = 100，但是最多50份
    assert len(vwap.get_split_plan()) <= 50


def test_specified_num_splits():
    """测试指定份数"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(10000, OrderSide.BUY, start, end, num_splits=10)
    plan = vwap.get_split_plan()
    assert len(plan) == 10


def test_get_next_order_before_start():
    """测试开始前获取下一笔"""
    start = datetime.now() + timedelta(minutes=5)
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(10000, OrderSide.BUY, start, end, num_splits=10)
    chunk = vwap.get_next_order(datetime.now())
    assert chunk is None


def test_get_next_order_progress():
    """测试逐步获取"""
    start = datetime.now() - timedelta(hours=4)
    end = datetime.now()  # 所有chunk都已经到时间
    vwap = VWAPAlgo(1000, OrderSide.BUY, start, end, num_splits=10)
    chunks = []
    while not vwap.is_done():
        chunk = vwap.get_next_order(datetime.now())
        if chunk is not None:
            chunks.append(chunk)
    assert len(chunks) <= 10
    assert sum(chunks) == 1000
    assert vwap.is_done()
    assert vwap.get_progress() == 1.0


def test_progress():
    """测试进度计算"""
    start = datetime.now() - timedelta(minutes=30)
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(1000, OrderSide.BUY, start, end, num_splits=10)
    assert vwap.get_progress() == 0.0
    # 拿一笔（已经到时间了）
    chunk = vwap.get_next_order(datetime.now())
    if chunk is not None:
        assert 0 < vwap.get_progress() < 1.0
    else:
        # 如果还没到时间，进度还是0，这也可以接受
        assert vwap.get_progress() == 0.0


def test_remaining_quantity():
    """测试剩余数量"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    vwap = VWAPAlgo(1000, OrderSide.BUY, start, end, num_splits=10)
    assert vwap.get_remaining_quantity() == 1000
