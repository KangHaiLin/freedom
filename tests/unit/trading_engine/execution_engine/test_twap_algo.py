"""
Unit tests for twap_algo.py
"""
import pytest
from datetime import datetime, timedelta
from src.trading_engine.execution_engine.twap_algo import TWAPAlgo
from src.trading_engine.base.base_order import OrderSide


def test_init():
    """测试初始化"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    twap = TWAPAlgo(10000, OrderSide.BUY, start, end, interval_seconds=300)
    assert twap.total_quantity == 10000
    assert twap.remaining_quantity == 10000
    assert not twap.is_done()


def test_calculate_num_intervals():
    """测试计算间隔数量"""
    start = datetime.now()
    end = start + timedelta(hours=4)  # 4小时 = 14400秒 / 300秒 = 48间隔
    twap = TWAPAlgo(10000, OrderSide.BUY, start, end, interval_seconds=300)
    assert len(twap.get_split_plan()) == 48


def test_get_next_order_first():
    """测试获取第一笔"""
    start = datetime.now() - timedelta(minutes=10)
    end = start + timedelta(hours=4)
    twap = TWAPAlgo(1000, OrderSide.BUY, start, end, interval_seconds=300, min_chunk=100)
    # 第一笔已经过了开始时间，立即返回
    chunk = twap.get_next_order(datetime.now())
    assert chunk is not None
    assert chunk > 0


def test_get_next_order_wait_interval():
    """测试需要等间隔"""
    start = datetime.now()
    end = start + timedelta(hours=4)
    twap = TWAPAlgo(1000, OrderSide.BUY, start, end, interval_seconds=300)
    # 第一笔
    chunk = twap.get_next_order(datetime.now())
    assert chunk is not None
    # 立即拿第二笔，还没到间隔，返回None
    chunk = twap.get_next_order(datetime.now())
    assert chunk is None


def test_progress():
    """测试进度"""
    start = datetime.now() - timedelta(hours=4)
    end = datetime.now()
    twap = TWAPAlgo(1000, OrderSide.BUY, start, end, interval_seconds=300)
    assert twap.get_progress() == 0.0
    done_chunks = 0
    while not twap.is_done():
        chunk = twap.get_next_order(datetime.now())
        if chunk is not None:
            done_chunks += 1
    assert twap.is_done()
    assert twap.get_progress() == 1.0
    assert sum(twap.get_split_plan()) == 1000
