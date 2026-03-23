"""
Unit tests for simulation trading
"""

from datetime import date, datetime

from src.strategy_research.base import BaseStrategy, TradeDirection, TradeRecord
from src.strategy_research.simulation_trading import SimulationConfig, SimulationEngine, SimulationOrder


class TestStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}


class BuyStrategy(BaseStrategy):
    """Strategy that buys 000001.SZ on first bar"""

    def on_bar(self, bar_data, current_date, portfolio):
        return {"000001.SZ": TradeDirection.BUY}


class BuyAllStrategy(BaseStrategy):
    """Strategy that buys everything"""

    def on_bar(self, bar_data, current_date, portfolio):
        return {"000001.SZ": TradeDirection.BUY, "600000.SH": TradeDirection.BUY}


def test_init():
    """Test initialization"""
    strategy = TestStrategy()
    config = SimulationConfig(initial_capital=100000)
    engine = SimulationEngine(strategy, config)

    assert engine is not None
    assert engine.account.cash == 100000
    assert len(engine.trades) == 0
    assert len(engine.daily_stats) == 0


def test_init_default_config():
    """Test initialization with default config"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    assert engine is not None
    assert engine.account.cash == 1000000  # Default from SimulationConfig


def test_simulation_order():
    """Test SimulationOrder class"""
    order = SimulationOrder(
        order_id=1,
        ts_code="000001.SZ",
        direction=TradeDirection.BUY,
        price=10.0,
        quantity=100,
        created_at=datetime.now(),
    )

    assert order.order_id == 1
    assert order.ts_code == "000001.SZ"
    assert order.direction == TradeDirection.BUY
    assert order.price == 10.0
    assert order.quantity == 100
    assert order.is_filled() is False


def test_place_order():
    """Test placing order"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 1000)
    assert order_id > 0
    assert len(engine._orders) == 1


def test_place_order_zero_quantity():
    """Test placing order with zero quantity returns -1"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 0)
    assert order_id == -1


def test_place_order_not_enough_cash():
    """Test placing buy order with insufficient cash"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    # Try to buy more than cash allows
    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 2000.0, 10000)
    assert order_id == -1  # Rejected


def test_cancel_order():
    """Test canceling order"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 1000)
    success = engine.cancel_order(order_id)
    assert success is True


def test_cancel_order_not_found():
    """Test canceling non-existent order returns False"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    success = engine.cancel_order(999)
    assert success is False


def test_buy_sell():
    """Test buy and sell"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    # Buy
    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 1000)
    trade = engine.match_bar({"000001.SZ": 10.0}, datetime.now())

    assert len(trade) == 1
    assert engine.account.cash < 1000000
    assert engine.account.count_positions() == 1
    assert len(engine.trades) == 1

    # Sell
    pos = engine.account.get_position("000001.SZ")
    assert pos.quantity == 1000

    order_id = engine.place_order("000001.SZ", TradeDirection.SELL, 10.5, 1000)
    trade = engine.match_bar({"000001.SZ": 10.5}, datetime.now())

    assert len(trade) == 1
    assert engine.account.count_positions() == 0
    assert engine.account.cash > 1000000  # Profit
    assert len(engine.trades) == 2
    assert engine.trades[1].pnl > 0


def test_match_tick_buy_filled():
    """Test tick matching for buy order that gets filled"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    trade = engine.match_tick("000001.SZ", 9.8)

    assert trade is not None
    assert trade.ts_code == "000001.SZ"
    assert trade.direction == TradeDirection.BUY
    assert len(engine.trades) == 1


def test_match_tick_buy_not_filled():
    """Test tick matching for buy order that doesn't get filled"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    trade = engine.match_tick("000001.SZ", 10.5)  # Current price higher than limit

    assert trade is None


def test_match_tick_sell_filled():
    """Test tick matching for sell order that gets filled"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    # Buy first
    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    engine.match_bar({"000001.SZ": 10.0}, datetime.now())

    engine.place_order("000001.SZ", TradeDirection.SELL, 11.0, 100)
    trade = engine.match_tick("000001.SZ", 11.5)  # Current price higher than limit

    assert trade is not None
    assert trade.direction == TradeDirection.SELL
    assert len(engine.trades) == 2


def test_match_tick_sell_not_filled():
    """Test tick matching for sell order that doesn't get filled"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.SELL, 10.0, 100)
    trade = engine.match_tick("000001.SZ", 9.5)  # Current price lower than limit

    assert trade is None


def test_match_tick_wrong_stock():
    """Test tick matching for different stock code doesn't match"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    trade = engine.match_tick("600000.SH", 10.0)

    assert trade is None


def test_match_tick_market_order_buy():
    """Test market order (price <= 0) always fills"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 0, 100)
    trade = engine.match_tick("000001.SZ", 10.0)

    assert trade is not None


def test_match_bar_multiple_orders():
    """Test matching multiple orders in one bar"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    engine.place_order("600000.SH", TradeDirection.BUY, 20.0, 50)

    trades = engine.match_bar({"000001.SZ": 10.0, "600000.SH": 20.0}, datetime.now())

    assert len(trades) == 2
    assert len(engine.trades) == 2


def test_match_bar_skips_already_filled():
    """Test matching skips already filled orders"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    order_id = engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    engine.cancel_order(order_id)

    trades = engine.match_bar({"000001.SZ": 10.0}, datetime.now())

    assert len(trades) == 0


def test_match_bar_skips_missing_price():
    """Test matching skips orders for stocks without price data"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    trades = engine.match_bar({"600000.SH": 20.0}, datetime.now())

    assert len(trades) == 0


def test_on_bar_empty_signals():
    """Test on_bar with no trading signals"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)
    current_date = date(2024, 1, 1)

    result = engine.on_bar([], current_date, {"000001.SZ": 10.0})

    assert result["success"] is True
    assert len(result["executed_orders"]) == 0
    assert len(result["filled_trades"]) == 0
    assert len(engine.daily_stats) == 1


def test_on_bar_buy_signal():
    """Test on-bar executing buy signal"""
    strategy = BuyStrategy()
    # Commission is 0.03% so we need enough cash to cover commission
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=105000))
    current_date = date(2024, 1, 1)

    result = engine.on_bar([], current_date, {"000001.SZ": 10.0})

    assert result["success"] is True
    assert len(result["executed_orders"]) == 1
    assert len(result["filled_trades"]) == 1
    assert engine.account.count_positions() == 1


def test_on_bar_buy_insufficient_cash():
    """Test on-bar buy when not enough cash (should skip)"""
    strategy = BuyStrategy()
    # Very little cash
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=500))
    current_date = date(2024, 1, 1)

    result = engine.on_bar([], current_date, {"000001.SZ": 10.0})
    # Need 100 * 10 = 1000 + commission, only have 500
    assert len(result["executed_orders"]) == 0


def test_on_bar_buy_invalid_price():
    """Test on-bar buy with invalid price (zero)"""
    strategy = BuyStrategy()
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=100000))
    current_date = date(2024, 1, 1)

    result = engine.on_bar([], current_date, {"000001.SZ": 0})
    assert len(result["executed_orders"]) == 0


def test_on_bar_sell_signal():
    """Test on-bar executing sell signal"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=100000))

    # Buy first
    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 1000)
    engine.match_bar({"000001.SZ": 10.0}, datetime.now())

    # Create strategy that sells it
    class SellStrategy(BaseStrategy):
        def on_bar(self, bar_data, current_date, portfolio):
            return {"000001.SZ": TradeDirection.SELL}

    engine._strategy = SellStrategy()
    current_date = date(2024, 1, 2)
    result = engine.on_bar([], current_date, {"000001.SZ": 11.0})

    assert len(result["executed_orders"]) == 1
    assert len(result["filled_trades"]) == 1
    assert engine.account.count_positions() == 0


def test_on_bar_multiple_buys():
    """Test on-bar with multiple buy signals"""
    strategy = BuyAllStrategy()
    # Need extra cash for commission
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=300000))
    current_date = date(2024, 1, 1)

    result = engine.on_bar([], current_date, {"000001.SZ": 10.0, "600000.SH": 20.0})

    assert result["success"] is True
    assert len(result["executed_orders"]) == 2
    assert len(result["filled_trades"]) == 2


def test_get_current_stats_empty():
    """Test get_current_stats when no daily stats yet"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    stats = engine.get_current_stats({"000001.SZ": 10.0})
    assert stats.total_assets == 1000000
    assert stats.daily_pnl == 0


def test_get_current_stats_with_history():
    """Test get_current_stats returns last when there is history"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy)

    engine.on_bar([], date(2024, 1, 1), {"000001.SZ": 10.0})
    stats = engine.get_current_stats({"000001.SZ": 10.5})

    assert stats == engine.daily_stats[-1]


def test_close_all():
    """Test closing all positions"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=100000))

    # Buy two stocks
    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    engine.place_order("600000.SH", TradeDirection.BUY, 20.0, 100)
    engine.match_bar({"000001.SZ": 10.0, "600000.SH": 20.0}, datetime.now())

    assert engine.account.count_positions() == 2

    # Close all
    closed = engine.close_all({"000001.SZ": 11.0, "600000.SH": 21.0})

    assert len(closed) == 2
    assert engine.account.count_positions() == 0
    assert len(engine.trades) == 4  # 2 buys + 2 sells


def test_close_all_missing_price():
    """Test close_all skips positions without current price"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=100000))

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)
    engine.match_bar({"000001.SZ": 10.0}, datetime.now())

    assert engine.account.count_positions() == 1

    closed = engine.close_all({"600000.SH": 20.0})  # No price for 000001

    assert len(closed) == 0
    assert engine.account.count_positions() == 1


def test_health_check():
    """Test health_check returns correct status"""
    strategy = TestStrategy()
    engine = SimulationEngine(strategy, SimulationConfig(initial_capital=100000))

    engine.place_order("000001.SZ", TradeDirection.BUY, 10.0, 100)

    health = engine.health_check()

    assert health["status"] == "ok"
    assert health["initial_capital"] == 100000
    assert health["current_cash"] == engine.account.cash
    assert health["total_orders"] == 1
    assert health["total_trades"] == 0
