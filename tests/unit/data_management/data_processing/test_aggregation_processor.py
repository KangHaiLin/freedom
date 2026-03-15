"""
Unit tests for aggregation_processor.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.aggregation_processor import AggregationProcessor


def create_test_data():
    """创建测试数据"""
    dates = pd.date_range('2024-01-01', '2024-01-31', freq='D')
    data = []
    for code in ['000001.SZ', '000002.SZ']:
        for date in dates:
            data.append({
                'ts_code': code,
                'trade_date': date,
                'open': 10 + np.random.rand(),
                'high': 11 + np.random.rand(),
                'low': 9 + np.random.rand(),
                'close': 10 + np.random.rand(),
                'volume': 10000 + np.random.randint(10000),
                'amount': 100000 + np.random.randint(100000)
            })
    return pd.DataFrame(data)


def test_aggregate_by_time():
    """测试按时间聚合"""
    processor = AggregationProcessor()
    df = create_test_data()

    # 按周聚合
    result = processor.aggregate_by_time(df, freq='W')
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
    assert 'open' in result.columns
    assert 'close' in result.columns


def test_aggregate_by_stock():
    """测试按股票聚合"""
    processor = AggregationProcessor()
    df = create_test_data()

    result = processor.aggregate_by_stock(df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2  # 两只股票
    assert 'close_mean' in result.columns


def test_rolling_aggregate():
    """测试滚动聚合"""
    processor = AggregationProcessor()
    df = pd.DataFrame({'close': [10, 11, 12, 13, 14, 15]})

    result = processor.rolling_aggregate(df, window=3, col='close', agg_func='mean')
    assert isinstance(result, pd.Series)
    assert len(result) == 6
    # 最后一个值是 (13+14+15)/3 = 14
    assert abs(result.iloc[-1] - 14) < 0.001


def test_expanding_aggregate():
    """测试扩张聚合"""
    processor = AggregationProcessor()
    df = pd.DataFrame({'close': [10, 12, 14, 16]})

    result = processor.expanding_aggregate(df, col='close', agg_func='mean')
    assert isinstance(result, pd.Series)
    assert len(result) == 4
    # 最后一个均值是 (10+12+14+16)/4 = 13
    assert abs(result.iloc[-1] - 13) < 0.001


def test_calculate_returns():
    """测试收益率计算"""
    processor = AggregationProcessor()
    df = pd.DataFrame({'close': [10, 11, 12, 13]})

    result = processor.calculate_returns(df, periods=1)
    assert 'return_1' in result.columns
    # 第一期NaN，第二期(11-10)/10=0.1
    assert abs(result['return_1'].iloc[1] - 0.1) < 0.001


def test_calculate_log_returns():
    """测试对数收益率计算"""
    processor = AggregationProcessor()
    df = pd.DataFrame({'close': [10, 11, 12]})

    result = processor.calculate_returns(df, periods=1, log_return=True)
    assert 'return_1' in result.columns
    assert not pd.isna(result['return_1'].iloc[1])


def test_calculate_cumulative_returns():
    """测试累计收益率"""
    processor = AggregationProcessor()
    df = pd.DataFrame({
        'close': [10, 11, 12, 13],
        'return_1': [np.nan, 0.1, (12-11)/11, (13-12)/12]
    })

    result = processor.calculate_cumulative_returns(df)
    assert abs(result.iloc[-1] - 0.3) < 0.01  # 从10到13，累计涨30%


def test_market_summary():
    """测试市场统计摘要"""
    processor = AggregationProcessor()
    df = create_test_data()
    df = processor.calculate_returns(df, price_col='close')

    summary = processor.market_summary(df)
    assert 'total_dates' in summary
    assert 'total_stocks' in summary
    assert 'avg_daily_return' in summary
