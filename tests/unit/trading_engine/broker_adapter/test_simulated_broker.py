"""
Unit tests for simulated_broker.py
"""
import pytest
from src.trading_engine.broker_adapter.simulated_broker import SimulatedBrokerAdapter
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.order_management.order import Order
from src.trading_engine.base.base_order import OrderSide, OrderStatus


def test_init():
    """测试初始化"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    assert broker.connect()
    assert broker.is_connected()
    assert broker.get_available_cash() == 100000.0


def test_get_account_info():
    """测试获取账户信息"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    info = broker.get_account_info()
    assert info['cash'] == 100000.0
    assert info['available_cash'] == 100000.0


def test_update_last_prices():
    """测试更新价格"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    broker.update_last_prices({
        '000001.SZ': 10.0,
        '000002.SZ': 20.0,
    })
    assert broker.get_last_price('000001.SZ') == 10.0
    prices = broker.get_last_prices(['000001.SZ', '000002.SZ'])
    assert prices['000001.SZ'] == 10.0
    assert prices['000002.SZ'] == 20.0


def test_submit_buy_order_success():
    """测试成功提交买单"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    broker.update_last_prices({'000001.SZ': 10.0})
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    success = broker.submit_order(order)
    assert success
    assert order.is_filled()
    # 检查现金减少
    # 成交金额 1000*10 = 10000，佣金大约5.2，现金应该减少 10000+5.2
    assert pm.get_cash() < 100000 - 10005
    # 检查持仓增加
    assert pm.get_position_count() == 1
    pos = pm.get_position('000001.SZ')
    assert pos.quantity == 1000


def test_submit_buy_order_insufficient_cash():
    """测试资金不足买单被拒绝"""
    pm = PortfolioManager(5000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    broker.update_last_prices({'000001.SZ': 10.0})
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    # 需要大约 10005，只有 5000
    success = broker.submit_order(order)
    assert not success
    assert order.status == OrderStatus.REJECTED


def test_submit_sell_order_success():
    """测试成功提交卖单"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    broker.update_last_prices({'000001.SZ': 10.0})

    # 先买入
    buy_order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    broker.submit_order(buy_order)

    # 更新价格上涨
    broker.update_last_prices({'000001.SZ': 12.0})

    # 卖出
    sell_order = Order.create_market_order('000001.SZ', OrderSide.SELL, 500)
    success = broker.submit_order(sell_order)
    assert success
    assert sell_order.is_filled()
    # 持仓剩余500
    pos = pm.get_position('000001.SZ')
    assert pos.quantity == 500
    # 现金增加
    assert pm.get_cash() > 100000 - (1000*10 + 5) + (500*12 - 15)


def test_submit_sell_order_insufficient_position():
    """测试持仓不足卖单被拒绝"""
    pm = PortfolioManager(100000.0)
    pm.add_position('000001.SZ', 500, 10.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    broker.update_last_prices({'000001.SZ': 10.0})
    sell_order = Order.create_market_order('000001.SZ', OrderSide.SELL, 1000)
    success = broker.submit_order(sell_order)
    assert not success
    assert sell_order.status == OrderStatus.REJECTED


def test_get_positions():
    """测试获取持仓"""
    pm = PortfolioManager(100000.0)
    pm.add_position('000001.SZ', 1000, 10.0)
    pm.add_position('000002.SZ', 500, 20.0)
    pm.update_prices({'000001.SZ': 12.0, '000002.SZ': 18.0})
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    positions = broker.get_positions()
    assert '000001.SZ' in positions
    assert '000002.SZ' in positions
    assert positions['000001.SZ']['quantity'] == 1000


def test_get_commission():
    """测试佣金计算"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    # 买入佣金
    comm = broker.get_commission(1000, 10.0, 1)  # 1=buy
    assert abs(comm - 5.2) < 0.1
    # 卖出佣金
    comm = broker.get_commission(1000, 10.0, 2)  # 2=sell
    assert abs(comm - 15.2) < 0.1


def test_health_check():
    """测试健康检查"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    health = broker.health_check()
    assert health['status'] == 'ok'
    assert health['connected']
    assert health['type'] == 'simulated'


def test_disconnect():
    """测试断开连接"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    assert broker.is_connected()
    broker.disconnect()
    assert not broker.is_connected()
