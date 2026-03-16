"""
Unit tests for simulation trading
"""
from datetime import datetime
from src.strategy_research.base import BaseStrategy, TradeDirection
from src.strategy_research.simulation_trading import SimulationEngine, SimulationConfig


class TestStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}


def test_init():
    """Test initialization"""
    strategy = TestStrategy()
    config = SimulationConfig(initial_capital=100000)
    engine = SimulationEngine(strategy, config)

    assert engine is not None
    assert engine.account.cash == 100000


def test_place_order():
    """Test placing order"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order('000001.SZ', TradeDirection.BUY, 10.0, 1000)
    assert order_id > 0
    assert len(engine._orders) == 1


def test_cancel_order():
    """Test canceling order"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order('000001.SZ', TradeDirection.BUY, 10.0, 1000)
    success = engine.cancel_order(order_id)
    assert success is True


def test_buy_sell():
    """Test buy and sell"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    # Buy
    order_id = engine.place_order('000001.SZ', TradeDirection.BUY, 10.0, 1000)
    trade = engine.match_bar({'000001.SZ': 10.0}, datetime.now())

    assert len(trade) == 1
    assert engine.account.cash < 1000000
    assert engine.account.count_positions() == 1
    assert len(engine.trades) == 1

    # Sell
    pos = engine.account.get_position('000001.SZ')
    assert pos.quantity == 1000

    order_id = engine.place_order('000001.SZ', TradeDirection.SELL, 10.5, 1000)
    trade = engine.match_bar({'000001.SZ': 10.5}, datetime.now())

    assert len(trade) == 1
    assert engine.account.count_positions() == 0
    assert engine.account.cash > 1000000  # Profit
    assert len(engine.trades) == 2
    assert engine.trades[1].pnl > 0
