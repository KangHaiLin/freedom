"""
Unit tests for execution_engine.py
"""

from datetime import datetime, timedelta

import pytest

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.broker_adapter.simulated_broker import SimulatedBrokerAdapter
from src.trading_engine.execution_engine.execution_engine import ExecutionEngine
from src.trading_engine.order_management.order_manager import OrderManager
from src.trading_engine.position_management.portfolio_manager import PortfolioManager


def test_init():
    """测试初始化"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    assert not engine.is_running()
    engine.start()
    assert engine.is_running()
    engine.stop()
    assert not engine.is_running()


def test_submit_vwap():
    """测试提交VWAP"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    start = datetime.now() - timedelta(hours=4)
    end = datetime.now()
    exec_id = engine.submit_vwap(
        "000001.SZ",
        OrderSide.BUY,
        1000,
        start,
        end,
        num_splits=10,
        min_chunk=100,
    )
    assert exec_id is not None
    active = engine.get_active_executions()
    assert len(active) == 1
    assert active[0]["total_quantity"] == 1000
    engine.stop()


def test_submit_twap():
    """测试提交TWAP"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    start = datetime.now() - timedelta(hours=4)
    end = datetime.now()
    exec_id = engine.submit_twap(
        "000001.SZ",
        OrderSide.BUY,
        1000,
        start,
        end,
        interval_seconds=300,
    )
    assert exec_id is not None
    active = engine.get_active_executions()
    assert len(active) == 1
    engine.stop()


def test_cancel_execution():
    """测试取消执行"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    start = datetime.now()
    end = start + timedelta(hours=4)
    exec_id = engine.submit_vwap("000001.SZ", OrderSide.BUY, 1000, start, end)
    assert engine.cancel_execution(exec_id)
    assert len(engine.get_active_executions()) == 0


def test_get_statistics():
    """测试获取统计"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    stats = engine.get_statistics()
    assert "active_executions" in stats
    assert "running" in stats


def test_health_check():
    """测试健康检查"""
    pm = PortfolioManager(100000.0)
    om = OrderManager()
    broker = SimulatedBrokerAdapter(pm)
    broker.connect()
    engine = ExecutionEngine(broker, om, pm, auto_start=False)
    health = engine.health_check()
    assert "status" in health
    assert "active_count" in health
    assert "thread_alive" in health
