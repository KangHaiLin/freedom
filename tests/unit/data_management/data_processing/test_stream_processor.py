"""
Unit tests for stream_processor.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.stream_processor import StreamProcessor


def create_tick_data(ts_code: str, n: int = 50):
    """创建模拟Tick数据"""
    np.random.seed(42)
    data = []
    price = 10.0
    base_time = pd.to_datetime('2024-01-01 09:30:00')
    for i in range(n):
        price = price * (1 + np.random.normal(0, 0.001))
        time = base_time + pd.Timedelta(minutes=i)
        data.append({
            'ts_code': ts_code,
            'trade_time': time,
            'open': price * 0.999,
            'high': price * 1.002,
            'low': price * 0.998,
            'close': price,
            'volume': np.random.randint(100, 1000),
            'amount': np.random.randint(1000, 10000)
        })
    return data


def test_stream_add_data():
    """测试添加数据到流"""
    stream = StreamProcessor(window_size=20)
    data = create_tick_data('000001.SZ', 30)

    result = stream.process(data)
    assert result['success'] is True
    assert result['processed_count'] == 30
    assert '000001.SZ' in result['results']
    assert '000001.SZ' in stream.stock_data


def test_sliding_window_size():
    """测试滑动窗口大小"""
    stream = StreamProcessor(window_size=20)
    data = create_tick_data('000001.SZ', 50)

    stream.process(data)
    window_df = stream.get_stock_window('000001.SZ')
    # 窗口大小限制为20，所以应该只保留最后20条
    assert len(window_df) == 20


def test_get_latest():
    """测试获取最新数据"""
    stream = StreamProcessor()
    data = create_tick_data('000001.SZ', 10)

    stream.process(data)
    latest = stream.get_latest('000001.SZ')

    assert latest is not None
    assert 'ts_code' in latest
    assert 'close' in latest
    assert latest['ts_code'] == '000001.SZ'


def test_get_latest_indicators():
    """测试获取最新指标"""
    stream = StreamProcessor(window_size=30)
    data = create_tick_data('000001.SZ', 50)

    stream.process(data)
    indicators = stream.get_latest_indicators('000001.SZ')

    assert indicators is not None
    assert 'latest_price' in indicators


def test_get_recent_klines():
    """测试获取最近N根K线"""
    stream = StreamProcessor(window_size=100)
    data = create_tick_data('000001.SZ', 50)

    stream.process(data)
    recent = stream.get_recent_klines('000001.SZ', count=10)

    assert len(recent) == 10


def test_set_window_size():
    """测试修改窗口大小"""
    stream = StreamProcessor(window_size=50)
    data = create_tick_data('000001.SZ', 50)
    stream.process(data)

    assert len(stream.get_stock_window('000001.SZ')) == 50

    # 修改窗口大小为30，应该裁剪到30条
    stream.set_window_size(30)
    assert len(stream.get_stock_window('000001.SZ')) == 30


def test_clear_stock():
    """测试清除指定股票"""
    stream = StreamProcessor()
    data1 = create_tick_data('000001.SZ', 10)
    data2 = create_tick_data('000002.SZ', 10)

    stream.process(data1)
    stream.process(data2)

    assert '000001.SZ' in stream.stock_data
    assert '000002.SZ' in stream.stock_data

    stream.clear_stock('000001.SZ')
    assert '000001.SZ' not in stream.stock_data
    assert '000002.SZ' in stream.stock_data


def test_clear_all():
    """测试清除所有数据"""
    stream = StreamProcessor()
    data1 = create_tick_data('000001.SZ', 10)
    data2 = create_tick_data('000002.SZ', 10)

    stream.process(data1)
    stream.process(data2)

    assert len(stream.stock_data) == 2
    stream.clear_all()
    assert len(stream.stock_data) == 0


def test_get_statistics():
    """测试获取统计信息"""
    stream = StreamProcessor(window_size=20)
    data1 = create_tick_data('000001.SZ', 10)
    data2 = create_tick_data('000002.SZ', 10)
    stream.process(data1)
    stream.process(data2)

    stats = stream.get_statistics()
    assert 'stock_count' in stats
    assert 'total_records' in stats
    assert 'window_size_config' in stats
    assert stats['stock_count'] == 2


def test_get_all_stocks():
    """测试获取所有股票列表"""
    stream = StreamProcessor()
    codes = ['000001.SZ', '000002.SZ', '000003.SZ']

    for code in codes:
        data = create_tick_data(code, 5)
        stream.process(data)

    result = stream.get_all_stocks()
    assert set(result) == set(codes)


def test_multiple_streams():
    """测试多股票增量处理"""
    stream = StreamProcessor(window_size=50)
    base_time = pd.to_datetime('2024-01-01 09:30:00')

    # 分批添加数据
    for i in range(5):
        for code in ['000001.SZ', '000002.SZ']:
            data = create_tick_data(code, 10)
            # 调整时间避免重复覆盖
            start_offset = i * 10
            for item in data:
                item['trade_time'] = base_time + pd.Timedelta(minutes=start_offset + item['trade_time'].minute)
            stream.process(data)

    assert len(stream.stock_data) == 2
    assert len(stream.get_stock_window('000001.SZ')) == 50
    assert len(stream.get_stock_window('000002.SZ')) == 50
