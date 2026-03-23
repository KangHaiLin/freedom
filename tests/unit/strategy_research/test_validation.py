"""
Unit tests for strategy validation
"""

import numpy as np
import pandas as pd

from src.strategy_research.backtest_engine import BacktestConfig, BacktestEngine
from src.strategy_research.base import BaseStrategy, TradeDirection
from src.strategy_research.strategy_validator import detect_overfit, scan_parameter
from src.strategy_research.strategy_validator.out_of_sample import rolling_window_test, split_sample_test
from src.strategy_research.strategy_validator.overfit_detector import calculate_information_ratio
from src.strategy_research.strategy_validator.param_sensitivity import grid_search, scan_parameter, sensitivity_summary


class DummyStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}


def test_calculate_information_ratio():
    """Test information ratio calculation"""
    returns = pd.Series(np.random.normal(0.0005, 0.01, 252))
    ir = calculate_information_ratio(returns)
    assert isinstance(ir, float)


def test_calculate_information_ratio_empty():
    """Test information ratio with empty series returns"""
    returns = pd.Series([])
    ir = calculate_information_ratio(returns)
    assert ir == 0.0


def test_detect_overfit():
    """Test overfitting detection"""
    data = []
    date = 20240101
    for i in range(252):
        data.append(
            {
                "trade_date": date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10 + i * 0.01,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)
    strategy = DummyStrategy()
    result = engine.run(strategy)

    detection = detect_overfit(result)
    assert "is_overfit" in detection
    assert "sharpe_ratio" in detection
    assert "calmar_ratio" in detection


def test_rolling_window_test():
    """Test rolling window out-of-sample testing"""
    # Generate 600 days of data (enough for 2 windows)
    data = []
    base_date = 20240101
    for i in range(600):
        data.append(
            {
                "trade_date": base_date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10 + (i % 100) * 0.01,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    config = BacktestConfig(initial_capital=100000)
    result = rolling_window_test(
        df,
        DummyStrategy,
        {},
        train_window_days=252,
        test_window_days=100,
        config=config,
    )

    assert "total_windows" in result
    assert (
        result["total_windows"] == 2
    )  # start=0 (window 0-251), then start=252 (window 252-503), start=504 → 504+252=756 > 600 → loop ends → total 2 windows
    assert len(result["results"]) == result["total_windows"]
    assert "average_train_return" in result
    assert "average_test_return" in result
    assert "return_decay" in result
    assert "overfit_suspected" in result


def test_rolling_window_test_not_enough_data():
    """Test rolling window with insufficient data returns error"""
    data = []
    base_date = 20240101
    for i in range(100):
        data.append(
            {
                "trade_date": base_date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    result = rolling_window_test(df, DummyStrategy, {}, train_window_days=252, test_window_days=60)
    assert "error" in result
    assert result["error"] == "Not enough data"


def test_split_sample_test():
    """Test simple split sample out-of-sample testing"""
    data = []
    base_date = 20240101
    for i in range(200):
        data.append(
            {
                "trade_date": base_date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    config = BacktestConfig(initial_capital=100000)
    result = split_sample_test(
        df,
        DummyStrategy,
        {},
        train_ratio=0.7,
        config=config,
    )

    assert result["train_size_days"] == 140
    assert result["test_size_days"] == 60
    assert "train_result" in result
    assert "test_result" in result
    assert "return_decay" in result
    assert "overfit_suspected" in result
    assert "train_result_obj" in result
    assert "test_result_obj" in result


def test_scan_parameter():
    """Test parameter scanning"""
    data = []
    date = 20240101
    for i in range(60):
        data.append(
            {
                "trade_date": date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    from src.strategy_research.base import BaseStrategy

    class TestStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            return {}

    base_params = {"param1": 10}
    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)

    result = scan_parameter(
        "param2",
        [1, 2, 3, 4, 5],
        base_params,
        TestStrategy,
        engine,
    )

    assert result["parameter_name"] == "param2"
    assert len(result["results"]) == 5
    assert "return_std" in result


def test_grid_search():
    """Test grid search for parameter optimization"""
    data = []
    base_date = 20240101
    for i in range(100):
        data.append(
            {
                "trade_date": base_date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    from src.strategy_research.base import BaseStrategy

    class TestStrategy(BaseStrategy):
        def __init__(self, params=None):
            super().__init__(params)
            self.param1 = self.params.get("param1", 10)
            self.param2 = self.params.get("param2", 20)

        def on_bar(self, bar_data, current_date, portfolio):
            return {}

    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)

    result = grid_search(
        {"param1": [10, 20], "param2": [1, 2]},
        {"param1": 10, "param2": 1},
        TestStrategy,
        engine,
    )

    assert "all_results" in result
    assert len(result["all_results"]) == 4
    assert "best_parameters" in result
    assert "best_result" in result
    assert result["optimize_metric"] == "sharpe_ratio"


def test_sensitivity_summary():
    """Test summarizing multiple sensitivity results"""
    from src.strategy_research.strategy_validator.param_sensitivity import scan_parameter

    data = []
    base_date = 20240101
    for i in range(50):
        data.append(
            {
                "trade_date": base_date + i,
                "ts_code": "000001.SZ",
                "open": 10,
                "high": 11,
                "low": 9.5,
                "close": 10,
                "vol": 1000000,
            }
        )
    df = pd.DataFrame(data)

    from src.strategy_research.base import BaseStrategy

    class TestStrategy(BaseStrategy):
        def __init__(self, params=None):
            super().__init__(params)

        def on_bar(self, bar_data, current_date, portfolio):
            return {}

    config = BacktestConfig(initial_capital=100000)
    engine = BacktestEngine(df, config)

    # Run two sensitivity scans
    result1 = scan_parameter("param1", [1, 2, 3], {}, TestStrategy, engine)
    result2 = scan_parameter("param2", [10, 20, 30], {}, TestStrategy, engine)

    summary = sensitivity_summary([result1, result2])

    assert "high_sensitivity_params" in summary
    assert "low_sensitivity_params" in summary
    assert summary["total_parameters"] == 2
