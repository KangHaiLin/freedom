"""
Unit tests for broker_adapter_manager.py
"""

import pytest

from src.trading_engine.broker_adapter.broker_adapter_manager import BrokerAdapterManager
from src.trading_engine.broker_adapter.simulated_broker import SimulatedBrokerAdapter
from src.trading_engine.position_management.portfolio_manager import PortfolioManager


def test_init():
    """测试初始化"""
    manager = BrokerAdapterManager()
    assert len(manager.get_adapter_names()) == 0


def test_register_adapter():
    """测试注册适配器"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("simulated", broker, default=True)
    assert "simulated" in manager.get_adapter_names()
    assert manager.default_adapter_name == "simulated"


def test_get_adapter():
    """测试获取适配器"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("simulated", broker, default=True)
    got = manager.get_adapter()
    assert got is broker
    got = manager.get_adapter("simulated")
    assert got is broker


def test_get_default():
    """测试获取默认"""
    pm = PortfolioManager(100000.0)
    broker1 = SimulatedBrokerAdapter(pm)
    broker2 = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("broker1", broker1)
    manager.register_adapter("broker2", broker2, default=True)
    assert manager.default_adapter_name == "broker2"
    assert manager.get_default_adapter() is broker2


def test_unregister_adapter():
    """测试注销适配器"""
    pm = PortfolioManager(100000.0)
    broker = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("simulated", broker)
    assert manager.unregister_adapter("simulated")
    assert "simulated" not in manager.get_adapter_names()


def test_connect_all():
    """测试连接所有"""
    pm = PortfolioManager(100000.0)
    broker1 = SimulatedBrokerAdapter(pm)
    broker2 = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("broker1", broker1)
    manager.register_adapter("broker2", broker2)
    results = manager.connect_all()
    assert results["broker1"]
    assert results["broker2"]
    assert broker1.is_connected()
    assert broker2.is_connected()


def test_disconnect_all():
    """测试断开所有"""
    pm = PortfolioManager(100000.0)
    broker1 = SimulatedBrokerAdapter(pm)
    broker2 = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("broker1", broker1)
    manager.register_adapter("broker2", broker2)
    manager.connect_all()
    manager.disconnect_all()
    assert not broker1.is_connected()
    assert not broker2.is_connected()


def test_health_check_all():
    """测试健康检查所有"""
    pm = PortfolioManager(100000.0)
    broker1 = SimulatedBrokerAdapter(pm)
    broker2 = SimulatedBrokerAdapter(pm)
    manager = BrokerAdapterManager()
    manager.register_adapter("broker1", broker1)
    manager.register_adapter("broker2", broker2)
    broker1.connect()
    results = manager.health_check_all()
    assert "broker1" in results
    assert "broker2" in results
