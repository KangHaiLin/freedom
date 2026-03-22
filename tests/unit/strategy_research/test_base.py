"""
Unit tests for strategy research base classes
"""

from src.strategy_research.base import BaseStrategy, OrderType, PositionSide, StrategyStatus, TradeDirection


def test_enums():
    """Test enums"""
    assert StrategyStatus.DRAFT.value == "draft"
    assert StrategyStatus.READY.value == "ready"
    assert TradeDirection.BUY.value == "BUY"
    assert PositionSide.LONG.value == "long"
    assert OrderType.MARKET.value == "market"


def test_base_strategy():
    """Test BaseStrategy abstract base"""

    class MyStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            return {}

    strategy = MyStrategy(strategy_name="Test", params={"param": 1})
    assert strategy.name == "Test"
    assert strategy.get_parameters() == {"param": 1}

    strategy.initialize()
    assert strategy.initialized is True
