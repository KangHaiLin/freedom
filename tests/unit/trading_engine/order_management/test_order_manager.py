"""
Unit tests for order_manager.py
"""
import pytest
from datetime import datetime, timedelta
from src.trading_engine.order_management.order import Order
from src.trading_engine.order_management.order_manager import OrderManager
from src.trading_engine.base.base_order import OrderSide, OrderStatus


def test_init():
    """测试初始化"""
    manager = OrderManager()
    assert manager.get_order_count() == 0


def test_add_order():
    """测试添加订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.add_order(order)
    assert order_id == order.order_id
    assert manager.get_order_count() == 1
    assert manager.get_order(order_id) is order


def test_add_order_empty_id():
    """测试添加没有ID的订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    # 清空ID
    order.order_id = ""
    order_id = manager.add_order(order)
    assert order_id == ""
    assert manager.get_order_count() == 0


def test_remove_order():
    """测试移除订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.add_order(order)
    assert manager.remove_order(order_id)
    assert manager.get_order_count() == 0
    assert not manager.remove_order("nonexistent")


def test_submit_order():
    """测试提交订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    assert order_id != ""
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None


def test_update_status_success():
    """测试成功更新状态"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.add_order(order)
    success, error = manager.update_order_status(order_id, OrderStatus.SUBMITTED)
    assert success
    assert error is None
    assert order.status == OrderStatus.SUBMITTED


def test_update_status_fail_not_exists():
    """测试更新不存在订单状态"""
    manager = OrderManager()
    success, error = manager.update_order_status("nonexistent", OrderStatus.SUBMITTED)
    assert not success
    assert "订单不存在" in error


def test_update_status_fail_invalid_transition():
    """测试非法状态转换"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.add_order(order)
    order.submit()
    order.fill(1000, 10.0, datetime.now())
    # FILLED 无法转换回 PENDING
    success, error = manager.update_order_status(order_id, OrderStatus.PENDING)
    assert not success
    assert "无效状态转换" in error


def test_cancel_order_success():
    """测试成功取消订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    success, error = manager.cancel_order(order_id)
    assert success
    assert order.status == OrderStatus.CANCELLED


def test_cancel_order_fail_already_filled():
    """测试取消已成交订单失败"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    manager.fill_order(order_id, 1000, 10.0, datetime.now())
    success, error = manager.cancel_order(order_id)
    assert not success
    assert "不可取消" in error


def test_fill_order_success_partial():
    """测试部分成交成功"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    success, error = manager.fill_order(order_id, 500, 10.0, datetime.now())
    assert success
    assert order.filled_quantity == 500
    assert order.status == OrderStatus.PARTIAL


def test_fill_order_success_full():
    """测试完全成交成功"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    success, error = manager.fill_order(order_id, 1000, 10.0, datetime.now())
    assert success
    assert order.filled_quantity == 1000
    assert order.status == OrderStatus.FILLED
    assert order.filled_at is not None


def test_fill_order_fail_over_quantity():
    """测试成交数量超过剩余数量失败"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.submit_order(order)
    success, error = manager.fill_order(order_id, 1500, 10.0, datetime.now())
    assert not success
    assert "超过剩余数量" in error


def test_reject_order():
    """测试拒绝订单"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order_id = manager.add_order(order)
    success, error = manager.reject_order(order_id, "资金不足")
    assert success
    assert order.status == OrderStatus.REJECTED
    assert order.extra_info['reject_reason'] == "资金不足"


def test_query_orders_by_status():
    """测试按状态查询"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.submit_order(order1)
    manager.add_order(order2)
    pending = manager.query_orders(status=[OrderStatus.PENDING])
    assert len(pending) == 1
    assert pending[0] == order2
    submitted = manager.query_orders(status=[OrderStatus.SUBMITTED])
    assert len(submitted) == 1


def test_query_orders_by_ts_code():
    """测试按股票代码查询"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.add_order(order1)
    manager.add_order(order2)
    result = manager.query_orders(ts_code='000001.SZ')
    assert len(result) == 1
    assert result[0] == order1


def test_query_orders_by_strategy_id():
    """测试按策略ID查询"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000, strategy_id='strategy1')
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000, strategy_id='strategy2')
    manager.add_order(order1)
    manager.add_order(order2)
    result = manager.query_orders(strategy_id='strategy1')
    assert len(result) == 1
    assert result[0] == order1


def test_query_orders_by_time():
    """测试按时间查询"""
    manager = OrderManager()
    order = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    manager.add_order(order)
    yesterday = datetime.now() - timedelta(days=1)
    tomorrow = datetime.now() + timedelta(days=1)
    result = manager.query_orders(start_time=yesterday, end_time=tomorrow)
    assert len(result) == 1


def test_get_active_orders():
    """测试获取活跃订单"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.submit_order(order1)
    manager.add_order(order2)
    manager.fill_order(order1.order_id, 1000, 10.0, datetime.now())
    active = manager.get_active_orders()
    # order1 已成交不是活跃，order2 还是 pending 活跃
    assert len(active) == 1
    assert active[0] == order2


def test_get_active_orders_by_ts_code():
    """测试按股票代码获取活跃订单"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.add_order(order1)
    manager.add_order(order2)
    active = manager.get_active_orders(ts_code='000001.SZ')
    assert len(active) == 1
    assert active[0].ts_code == '000001.SZ'


def test_get_statistics():
    """测试获取统计信息"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.add_order(order1)
    manager.submit_order(order2)
    stats = manager.get_statistics()
    assert stats['total'] == 2
    assert stats['PENDING'] == 1
    assert stats['SUBMITTED'] == 1
    assert stats['active'] == 2


def test_clear_all():
    """测试清空"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.add_order(order1)
    manager.add_order(order2)
    assert manager.get_order_count() == 2
    manager.clear_all()
    assert manager.get_order_count() == 0


def test_get_all_orders():
    """测试获取所有订单"""
    manager = OrderManager()
    order1 = Order.create_market_order('000001.SZ', OrderSide.BUY, 1000)
    order2 = Order.create_market_order('000002.SZ', OrderSide.BUY, 1000)
    manager.add_order(order1)
    manager.add_order(order2)
    all_orders = manager.get_all_orders()
    assert len(all_orders) == 2
