"""
Unit tests for strategy validation
"""
import pandas as pd
import numpy as np
from src.strategy_research.base import BaseStrategy, TradeDirection
from src.strategy_research.backtest_engine import BacktestEngine, BacktestConfig
from src.strategy_research.strategy_validator import detect_overfit, scan_parameter
from src.strategy_research.strategy_validator.overfit_detector import calculate_information_ratio


class DummyStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}


def test_calculate_information_ratio():
    """Test information ratio calculation"""
    returns = pd.Series(np.random.normal(0.0005, 0.01, 252))
    ir = calculate_information_ratio(returns)
    assert isinstance(ir, float)


def test_detect_overfit():
    """Test overfitting detection"""
    data = []
    date = 20240101
    for i in range(252):
        data.append({
            'trade_date': date + i,
            'ts_code': '000001.SZ',
            'open': 10,
            'high': 11,
            'low': 9.5,
            'close': 10 + i * 0.01,
            'vol': 1000000,
        })
    df = pd.DataFrame(data)

    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)
    strategy = DummyStrategy()
    result = engine.run(strategy)

    detection = detect_overfit(result)
    assert 'is_overfit' in detection
    assert 'sharpe_ratio' in detection
    assert 'calmar_ratio' in detection


def test_scan_parameter():
    """Test parameter scanning"""
    data = []
    date = 20240101
    for i in range(60):
        data.append({
            'trade_date': date + i,
            'ts_code': '000001.SZ',
            'open': 10,
            'high': 11,
            'low': 9.5,
            'close': 10,
            'vol': 1000000,
        })
    df = pd.DataFrame(data)

    from src.strategy_research.base import BaseStrategy

    class TestStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            return {}

    base_params = {'param1': 10}
    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)

    result = scan_parameter(
        'param2',
        [1, 2, 3, 4, 5],
        base_params,
        TestStrategy,
        engine,
    )

    assert result['parameter_name'] == 'param2'
    assert len(result['results']) == 5
    assert 'return_std' in result
