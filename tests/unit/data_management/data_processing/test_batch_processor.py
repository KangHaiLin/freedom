"""
Unit tests for batch_processor.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.batch_processor import BatchProcessor


def create_large_data(size: int = 50000):
    """创建大数据集"""
    np.random.seed(42)
    data = {
        'ts_code': np.random.choice(['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ'], size=size),
        'trade_date': pd.date_range('2024-01-01', periods=size//4).repeat(4),
        'open': 10 + np.random.rand(size),
        'high': 11 + np.random.rand(size),
        'low': 9 + np.random.rand(size),
        'close': 10 + np.random.rand(size),
        'volume': np.random.randint(1000, 100000, size=size),
    }
    return pd.DataFrame(data)


def test_process_pipeline():
    """测试处理流水线"""
    processor = BatchProcessor(chunk_size=1000)

    # 简单流水线：先筛选再添加列
    def add_return(df):
        df['return'] = df['close'].pct_change()
        return df

    df = create_large_data(1000)
    result = processor.process_pipeline(df, [add_return])

    assert isinstance(result, pd.DataFrame)
    assert 'return' in result.columns
    assert len(result) == len(df)


def test_process_in_chunks():
    """测试分块处理"""
    processor = BatchProcessor(chunk_size=100)

    def add_col(df):
        df['new_col'] = df['close'] * 2
        return df

    df = create_large_data(500)
    result = processor.process_in_chunks(df, [add_col])

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 500
    assert 'new_col' in result.columns
    assert (result['new_col'] == result['close'] * 2).all()


def test_process_by_stock():
    """测试按股票分组处理"""
    processor = BatchProcessor()

    # 对每个股票计算累计收益
    def calc_cum_return(df):
        df = df.sort_values('trade_date')
        df['cum_return'] = (1 + df['close'].pct_change()).cumprod() - 1
        return df

    df = create_large_data(1000)
    result = processor.process_by_stock(df, calc_cum_return, code_col='ts_code')

    assert isinstance(result, pd.DataFrame)
    assert 'cum_return' in result.columns
    # 每个股票至少一条数据
    assert len(result) == len(df)


def test_process():
    """测试统一process入口"""
    processor = BatchProcessor()

    def add_col(df):
        df['test'] = 1
        return df

    df = create_large_data(100)
    result = processor.process(df, [add_col])

    assert result.is_success()
    assert 'input_rows' in result.metrics
    assert result.data is not None
    assert 'test' in result.data.columns


def test_empty_data():
    """测试空数据处理"""
    processor = BatchProcessor()
    df = pd.DataFrame()

    def add_col(df):
        df['test'] = 1
        return df

    result = processor.process(df, [add_col])
    assert not result.is_success()


def test_large_data_processing():
    """测试大数据分块处理"""
    processor = BatchProcessor(chunk_size=1000)

    def simple_process(df):
        df['processed'] = df['close'] * df['volume']
        return df

    df = create_large_data(10000)
    result = processor.process(df, [simple_process])

    assert result.is_success()
    assert len(result.data) == 10000
    assert 'processed' in result.data.columns
