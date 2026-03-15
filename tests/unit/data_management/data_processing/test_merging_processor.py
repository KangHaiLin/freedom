"""
Unit tests for merging_processor.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.merging_processor import MergingProcessor


def create_market_data():
    """创建行情测试数据"""
    dates = pd.date_range('2024-01-01', '2024-01-10')
    data = []
    for code in ['000001.SZ', '000002.SZ']:
        for date in dates:
            data.append({
                'ts_code': code,
                'trade_date': date,
                'close': 10 + np.random.rand(),
                'volume': 10000 + np.random.randint(10000)
            })
    return pd.DataFrame(data)


def create_fundamental_data():
    """创建基本面测试数据，只在季度末更新"""
    data = [
        {'ts_code': '000001.SZ', 'trade_date': pd.to_datetime('2023-12-31'), 'pe': 15.2, 'pb': 1.8, 'roe': 0.12},
        {'ts_code': '000001.SZ', 'trade_date': pd.to_datetime('2024-01-01'), 'pe': 15.2, 'pb': 1.8, 'roe': 0.12},
        {'ts_code': '000001.SZ', 'trade_date': pd.to_datetime('2024-03-31'), 'pe': 16.5, 'pb': 1.9, 'roe': 0.13},
        {'ts_code': '000002.SZ', 'trade_date': pd.to_datetime('2023-12-31'), 'pe': 10.5, 'pb': 1.2, 'roe': 0.08},
        {'ts_code': '000002.SZ', 'trade_date': pd.to_datetime('2024-01-01'), 'pe': 10.5, 'pb': 1.2, 'roe': 0.08},
        {'ts_code': '000002.SZ', 'trade_date': pd.to_datetime('2024-03-31'), 'pe': 11.2, 'pb': 1.3, 'roe': 0.09},
    ]
    return pd.DataFrame(data)


def test_merge_market_fundamental():
    """测试合并行情和基本面"""
    processor = MergingProcessor()
    market = create_market_data()
    fund = create_fundamental_data()

    # 我们只取1月数据，基本面只有去年底，所以前向填充
    merged = processor.merge_market_fundamental(market, fund, ffill=True)

    assert isinstance(merged, pd.DataFrame)
    assert len(merged) == len(market)
    # 因为两边列名不重复，所以不会添加后缀
    assert 'pe' in merged.columns
    assert 'pb' in merged.columns
    # 基本面应该都被填充了（从2023-12-31填充到整个1月）
    assert merged['pe'].notna().all()


def test_concat_datasets():
    """测试垂直拼接"""
    processor = MergingProcessor()
    df1 = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    df2 = pd.DataFrame({'a': [7, 8, 9], 'b': [10, 11, 12]})

    result = processor.concat_datasets([df1, df2])
    assert len(result) == 6
    assert list(result['a']) == [1, 2, 3, 7, 8, 9]


def test_join_datasets():
    """测试水平连接"""
    processor = MergingProcessor()
    df1 = pd.DataFrame({'ts_code': ['000001', '000002'], 'close': [10, 20]})
    df2 = pd.DataFrame({'ts_code': ['000001', '000002'], 'volume': [1000, 2000]})

    result = processor.join_datasets([df1, df2], on=['ts_code'])
    assert len(result) == 2
    assert 'close' in result.columns
    assert 'volume' in result.columns
    assert result.iloc[0]['volume'] == 1000


def test_align_time_range_intersection():
    """测试时间范围对齐-交集"""
    processor = MergingProcessor()

    # 数据集1: 1-5日
    df1 = pd.DataFrame({
        'trade_date': pd.date_range('2024-01-01', '2024-01-05'),
        'value': [1, 2, 3, 4, 5]
    })

    # 数据集2: 3-7日
    df2 = pd.DataFrame({
        'trade_date': pd.date_range('2024-01-03', '2024-01-07'),
        'value': [3, 4, 5, 6, 7]
    })

    aligned = processor.align_time_range([df1, df2], intersection=True)
    assert len(aligned) == 2
    # 交集是3-5日，共3天
    assert len(aligned[0]) == 3
    assert len(aligned[1]) == 3


def test_align_time_range_union():
    """测试时间范围对齐-并集"""
    processor = MergingProcessor()

    df1 = pd.DataFrame({
        'trade_date': pd.date_range('2024-01-01', '2024-01-03'),
        'value': [1, 2, 3]
    })

    df2 = pd.DataFrame({
        'trade_date': pd.date_range('2024-01-03', '2024-01-05'),
        'value': [3, 4, 5]
    })

    aligned = processor.align_time_range([df1, df2], intersection=False, fill_missing='ffill')
    assert len(aligned) == 2
    # 并集是1-5日，共5天
    assert len(aligned[0]) == 5
    assert len(aligned[1]) == 5


def test_process_dispatch():
    """测试process分发"""
    processor = MergingProcessor()

    df1 = create_market_data()
    df2 = create_fundamental_data()

    result = processor.process([df1, df2], merge_type='market_fundamental')
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
