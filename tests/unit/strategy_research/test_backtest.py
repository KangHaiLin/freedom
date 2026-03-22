"""
Unit tests for backtest engine
"""

import numpy as np
import pandas as pd

from src.strategy_research.backtest_engine import BacktestConfig, BacktestEngine
from src.strategy_research.backtest_engine.performance_calculator import calculate_max_drawdown, calculate_sharpe_ratio
from src.strategy_research.base import BaseStrategy, TradeDirection


class SimpleBuyHoldStrategy(BaseStrategy):
    """Simple buy and hold strategy for testing"""

    def on_bar(self, bar_data, current_date, portfolio):
        signals = {}
        for _, row in bar_data.iterrows():
            if len(portfolio.get_all_positions()) == 0:
                signals[row["ts_code"]] = TradeDirection.BUY
        return signals


def test_simple_backtest():
    """Test simple backtest with buy-and-hold"""
    # Create test data
    data = [
        {
            "trade_date": 20240101,
            "ts_code": "000001.SZ",
            "open": 10,
            "high": 11,
            "low": 9.5,
            "close": 10,
            "vol": 1000000,
        },
        {
            "trade_date": 20240102,
            "ts_code": "000001.SZ",
            "open": 10,
            "high": 11,
            "low": 9.5,
            "close": 10.2,
            "vol": 1000000,
        },
        {
            "trade_date": 20240103,
            "ts_code": "000001.SZ",
            "open": 10.2,
            "high": 11.5,
            "low": 10,
            "close": 10.5,
            "vol": 1000000,
        },
        {
            "trade_date": 20240104,
            "ts_code": "000001.SZ",
            "open": 10.5,
            "high": 12,
            "low": 10.3,
            "close": 11,
            "vol": 1000000,
        },
        {
            "trade_date": 20240105,
            "ts_code": "000001.SZ",
            "open": 11,
            "high": 12.5,
            "low": 10.8,
            "close": 11.5,
            "vol": 1000000,
        },
    ]
    df = pd.DataFrame(data)

    config = BacktestConfig(initial_capital=100000, close_at_end=True)
    engine = BacktestEngine(df, config)
    strategy = SimpleBuyHoldStrategy()
    result = engine.run(strategy)

    assert result.strategy_name == "SimpleBuyHoldStrategy"
    assert result.initial_capital == 100000
    assert result.final_capital > 100000  # Price goes up
    assert result.total_pnl_pct > 0
    assert result.total_trades == 2  # Buy + close-all sell
    assert result.winning_trades == 1


def test_performance_calculator():
    """Test performance calculation"""
    # Test sharpe ratio
    returns = pd.Series([0.01, 0.02, -0.005, 0.015, -0.01])
    sharpe = calculate_sharpe_ratio(returns, 0.03)
    assert sharpe > 0

    # Test max drawdown
    cum = pd.Series([1.0, 1.02, 1.05, 1.03, 1.08, 1.04, 1.10])
    max_dd, peak, valley = calculate_max_drawdown(cum)
    assert max_dd > 0
    assert max_dd < (1.08 - 1.04) / 1.08 + 0.001


def test_position_limits():
    """Test position limit configuration"""
    data = [
        {"trade_date": 20240101, "ts_code": "000001.SZ", "close": 10},
        {"trade_date": 20240101, "ts_code": "000002.SZ", "close": 20},
        {"trade_date": 20240101, "ts_code": "000003.SZ", "close": 30},
    ]
    df = pd.DataFrame(data)

    class MultiBuyStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            signals = {}
            for _, row in bar_data.iterrows():
                signals[row["ts_code"]] = TradeDirection.BUY
            return signals

    # Single position max ratio 50%
    config = BacktestConfig(
        initial_capital=100000,
        single_position_max_ratio=0.5,
    )
    engine = BacktestEngine(df, config)
    strategy = MultiBuyStrategy()
    result = engine.run(strategy)

    # Only the first should be filled partially due to ratio limit
    assert result.total_trades >= 1
