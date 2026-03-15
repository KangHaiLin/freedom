"""
Unit tests for order_splitter.py
"""
import pytest
from src.trading_engine.execution_engine.order_splitter import OrderSplitter


def test_split_equal():
    """测试等份额拆分"""
    chunks = OrderSplitter.split_equal(1000, 10, 100)
    assert len(chunks) == 10
    assert sum(chunks) == 1000
    # 都应该是100
    for c in chunks:
        assert c == 100


def test_split_equal_remainder():
    """测试有余数的等份额拆分"""
    chunks = OrderSplitter.split_equal(1005, 10, 100)
    assert len(chunks) == 10
    assert sum(chunks) == 1005
    # 前5个101，后5个100 = 5*101+5*100= 505+500=1005


def test_split_vanilla():
    """测试简单受限拆分"""
    chunks = OrderSplitter.split_vanilla(10000, 1000, 100)
    assert len(chunks) == 10
    assert all(c == 1000 for c in chunks)
    assert sum(chunks) == 10000


def test_split_vanilla_remainder():
    """测试有余数简单拆分"""
    chunks = OrderSplitter.split_vanilla(10500, 1000, 100)
    assert len(chunks) == 11
    assert sum(chunks) == 10500
    assert sum(1 for c in chunks if c == 1000) == 10


def test_split_random():
    """测试随机拆分"""
    chunks = OrderSplitter.split_random(1000, 10, 100, 200, seed=42)
    assert len(chunks) == 10
    assert sum(chunks) == 1000
    assert all(100 <= c <= 200 for c in chunks)


def test_split_by_volume():
    """测试按成交量拆分"""
    volumes = [10000, 20000, 30000]  # 三个时间段成交量
    chunks = OrderSplitter.split_by_volume(3000, volumes, 0.1, 100, 1000)
    # 各时间段按比例 1000*0.1=100, 20000*0.1=200, 30000*0.1=300 → 总和600？不对，总目标是3000
    # 哦总目标3000，参与率0.1 → 每段是vol*0.1
    assert sum(chunks) == 3000


def test_calculate_optimal_splits():
    """测试计算最优拆分"""
    # 大单100000，日均成交1000000 → 100000/1000000 = 0.1，正好目标参与率0.1 → 1份
    splits = OrderSplitter.calculate_optimal_splits(100000, 1000000, 0.1)
    assert splits == 1

    # 大单500000，日均成交1000000 → 0.5 → 需要5份
    splits = OrderSplitter.calculate_optimal_splits(500000, 1000000, 0.1)
    assert splits == 5
