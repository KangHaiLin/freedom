"""
Integration tests for StrategyResearchManager
"""
import tempfile
import pandas as pd
from src.strategy_research.strategy_manager import StrategyResearchManager
from src.strategy_research.base import StrategyStatus


def test_create_and_backtest():
    """Test full workflow: create strategy -> backtest -> report"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyResearchManager(
            storage_dir=f"{tmpdir}/strategies",
            strategy_dir=tmpdir,
        )

        # Create strategy
        result = manager.create_strategy(
            strategy_id="test-bh",
            strategy_name="Buy and Hold",
            class_path="test_integration.TestBuyHold",
            description="Simple buy and hold",
            author="test",
            params={},
            tags=['buy_hold'],
        )

        assert result['success'] is True

        # List strategies
        strategies = manager.list_strategies()
        assert len(strategies) == 1

        # Health check
        health = manager.health_check()
        assert health['status'] == 'ok'
        assert health['strategies'] == 1


def test_backtest_custom():
    """Test backtest custom strategy"""
    from src.strategy_research.base import BaseStrategy, TradeDirection

    class BuyHoldStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            signals = {}
            for _, row in bar_data.iterrows():
                if len(portfolio.get_all_positions()) == 0:
                    signals[row['ts_code']] = TradeDirection.BUY
            return signals

    data = [
        {'trade_date': 20240101, 'ts_code': '000001.SZ', 'close': 10},
        {'trade_date': 20240102, 'ts_code': '000001.SZ', 'close': 10.2},
        {'trade_date': 20240103, 'ts_code': '000001.SZ', 'close': 10.5},
    ]
    df = pd.DataFrame(data)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyResearchManager(storage_dir=f"{tmpdir}/strategies")
        result = manager.backtest_custom(BuyHoldStrategy, {}, df)

        assert result.total_pnl > 0
        assert result.total_trades == 2  # Buy + close-all sell
