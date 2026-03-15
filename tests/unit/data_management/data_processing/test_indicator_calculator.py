"""
Unit tests for indicator_calculator.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.indicator_calculator import IndicatorCalculator


def create_price_data(n: int = 100):
    """创建模拟价格数据"""
    np.random.seed(42)
    prices = [10.0]
    for i in range(n-1):
        change = np.random.normal(0, 0.02)
        next_price = prices[-1] * (1 + change)
        prices.append(next_price)

    data = {
        'open': [p * (1 - 0.01) for p in prices],
        'high': [p * (1 + 0.02) for p in prices],
        'low': [p * (1 - 0.02) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000, 10000) for _ in prices],
        'amount': [np.random.randint(10000, 100000) for _ in prices]
    }
    dates = pd.date_range('2024-01-01', periods=n)
    return pd.DataFrame(data, index=dates)


def test_calculate_sma():
    """测试简单移动平均"""
    calc = IndicatorCalculator()
    df = create_price_data(50)
    result = calc.calculate_sma(df, windows=[5, 10])

    assert 'sma_5' in result.columns
    assert 'sma_10' in result.columns
    assert not pd.isna(result['sma_5'].iloc[-1])
    assert not pd.isna(result['sma_10'].iloc[-1])


def test_calculate_ema():
    """测试指数移动平均"""
    calc = IndicatorCalculator()
    df = create_price_data(50)
    result = calc.calculate_ema(df, windows=[12])

    assert 'ema_12' in result.columns
    assert not pd.isna(result['ema_12'].iloc[-1])


def test_calculate_rsi():
    """测试RSI"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_rsi(df, window=14)

    assert 'rsi_14' in result.columns
    # RSI应该在0-100之间
    assert result['rsi_14'].dropna().between(0, 100).all()


def test_calculate_kdj():
    """测试KDJ"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_kdj(df)

    assert 'k_9' in result.columns
    assert 'd_9' in result.columns
    assert 'j_9' in result.columns
    # KDJ应该在合理范围
    assert result['k_9'].dropna().between(0, 100).all()


def test_calculate_macd():
    """测试MACD"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_macd(df)

    assert 'macd_dif' in result.columns
    assert 'macd_dea' in result.columns
    assert 'macd_bar' in result.columns
    assert not pd.isna(result['macd_dif'].iloc[-1])


def test_calculate_boll():
    """测试布林带"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_boll(df)

    assert 'boll_mid_20' in result.columns
    assert 'boll_up_20' in result.columns
    assert 'boll_down_20' in result.columns
    # 上轨 > 中轨 > 下轨（去掉开头的NaN）
    valid = result.dropna(subset=['boll_up_20', 'boll_mid_20', 'boll_down_20'])
    assert (valid['boll_up_20'] >= valid['boll_mid_20']).all()
    assert (valid['boll_mid_20'] >= valid['boll_down_20']).all()


def test_calculate_vwap():
    """测试VWAP"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_vwap(df)

    assert 'vwap' in result.columns
    assert not pd.isna(result['vwap'].iloc[-1])


def test_calculate_obv():
    """测试OBV"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_obv(df)

    assert 'obv' in result.columns
    assert not pd.isna(result['obv'].iloc[-1])


def test_calculate_adx():
    """测试ADX"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.calculate_adx(df)

    assert f'adx_14' in result.columns
    # ADX应该在0-100之间
    assert result[f'adx_14'].dropna().between(0, 100).all()


def test_batch_calculate_multiple_indicators():
    """测试批量计算多个指标"""
    calc = IndicatorCalculator()
    df = create_price_data(100)
    result = calc.process(df, indicators=['sma', 'rsi', 'macd'])

    # 检查多个指标都被计算
    assert any(col.startswith('sma_') for col in result.columns)
    assert any(col.startswith('rsi_') for col in result.columns)
    assert 'macd_dif' in result.columns


def test_fundamental_derivatives():
    """测试基本面衍生指标"""
    calc = IndicatorCalculator()
    df = pd.DataFrame({
        'pe': [10, 15, 20, 25, 30],
        'pb': [1, 1.5, 2, 2.5, 3],
        'roe': [0.05, 0.10, 0.15, 0.20, 0.25],
        'net_profit': [100, 110, 120, 130, 140],
        'revenue': [1000, 1100, 1200, 1300, 1400]
    })

    result = calc.calculate_fundamental_derivatives(df)
    assert 'pe_percentile' in result.columns
    assert 'pb_percentile' in result.columns
    assert 'earnings_yoy' in result.columns
    assert 'revenue_yoy' in result.columns
