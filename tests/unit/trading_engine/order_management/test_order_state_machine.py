"""
Unit tests for order_state_machine.py
"""
import pytest
from src.trading_engine.order_management.order_state_machine import OrderStateMachine
from src.trading_engine.order_management.order import Order
from src.trading_engine.base.base_order import OrderSide, OrderStatus


def test_valid_transitions_from_pending():
    """测试从PENDING的合法转换"""
    assert OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.SUBMITTED)
    assert OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.CANCELLED)
    assert OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.REJECTED)
    assert not OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.FILLED)
    assert not OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.PARTIAL)


def test_valid_transitions_from_submitted():
    """测试从SUBMITTED的合法转换"""
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.PARTIAL)
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.FILLED)
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.CANCELLED)
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.REJECTED)
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.EXPIRED)


def test_terminal_states():
    """测试终态"""
    terminal_states = [
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    ]
    for status in terminal_states:
        assert OrderStateMachine.is_terminal(status)
        assert not OrderStateMachine.is_active(status)


def test_active_states():
    """测试活跃状态"""
    active_states = [
        OrderStatus.PENDING,
        OrderStatus.SUBMITTED,
        OrderStatus.PARTIAL,
    ]
    for status in active_states:
        assert not OrderStateMachine.is_terminal(status)
        assert OrderStateMachine.is_active(status)


def test_same_state_transition_allowed():
    """测试相同状态转换允许"""
    assert OrderStateMachine.can_transition(OrderStatus.PENDING, OrderStatus.PENDING)
    assert OrderStateMachine.can_transition(OrderStatus.SUBMITTED, OrderStatus.SUBMITTED)


def test_get_available_transitions():
    """测试获取可用转换"""
    transitions = OrderStateMachine.get_available_transitions(OrderStatus.PENDING)
    assert OrderStatus.SUBMITTED in transitions
    assert OrderStatus.CANCELLED in transitions
    assert OrderStatus.REJECTED in transitions
    assert len(transitions) == 3


def test_validate_transition_good():
    """测试验证合法转换"""
    error = OrderStateMachine.validate_transition(OrderStatus.PENDING, OrderStatus.SUBMITTED)
    assert error is None


def test_validate_transition_bad():
    """测试验证非法转换"""
    error = OrderStateMachine.validate_transition(OrderStatus.PENDING, OrderStatus.FILLED)
    assert error is not None
    assert '无效状态转换' in error
    assert 'PENDING → FILLED' in error


def test_transition_success():
    """测试执行转换成功"""
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    assert order.status == OrderStatus.PENDING
    success = OrderStateMachine.transition(order, OrderStatus.SUBMITTED)
    assert success
    assert order.status == OrderStatus.SUBMITTED


def test_transition_fail():
    """测试执行转换失败"""
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    # FILLED 是终态，不能转换到 PENDING
    order.submit()
    order.fill(1000, 10.0, order.created_at)
    assert order.status == OrderStatus.FILLED
    success = OrderStateMachine.transition(order, OrderStatus.PENDING)
    assert not success
    assert order.status == OrderStatus.FILLED  # 保持不变
