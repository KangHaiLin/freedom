"""
Unit tests for base_order.py
"""
import pytest
from datetime import datetime
from src.trading_engine.base.base_order import BaseOrder, OrderSide, OrderType, OrderStatus


class ConcreteOrder(BaseOrder):
    """具体实现用于测试抽象基类"""

    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL

    def get_remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    def is_partial_filled(self) -> bool:
        return self.status == OrderStatus.PARTIAL

    def can_cancel(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL]

    def fill(self, filled_quantity: int, filled_price: float, filled_time: datetime) -> None:
        self.filled_quantity += filled_quantity
        if self.filled_avg_price is None:
            self.filled_avg_price = filled_price
        else:
            total = self.filled_avg_price * (self.filled_quantity - filled_quantity) + filled_price * filled_quantity
            self.filled_avg_price = total / self.filled_quantity

        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_at = filled_time
        else:
            self.status = OrderStatus.PARTIAL
        self.updated_at = filled_time

    def cancel(self) -> None:
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now()

    def reject(self) -> None:
        self.status = OrderStatus.REJECTED
        self.updated_at = datetime.now()

    def submit(self) -> None:
        self.status = OrderStatus.SUBMITTED
        self.submitted_at = datetime.now()
        self.updated_at = datetime.now()

    def can_trigger(self, current_price: float) -> bool:
        if self.order_type not in [OrderType.STOP, OrderType.STOP_LIMIT]:
            return False
        if self.stop_price is None:
            return False
        # 买入止损：价格上涨到止损价触发；卖出止损：价格下跌到止损价触发
        if self.is_buy():
            return current_price >= self.stop_price
        else:
            return current_price <= self.stop_price

    def get_notional(self) -> float:
        if self.price is not None:
            return self.quantity * self.price
        if self.filled_avg_price is not None:
            return self.quantity * self.filled_avg_price
        return 0.0

    def get_filled_notional(self) -> float:
        if self.filled_avg_price is None:
            return 0.0
        return self.filled_quantity * self.filled_avg_price

    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'ts_code': self.ts_code,
            'side': self.side.name,
            'quantity': self.quantity,
            'filled_quantity': self.filled_quantity,
            'order_type': self.order_type.name,
            'price': self.price,
            'status': self.status.name,
            'filled_avg_price': self.filled_avg_price,
        }


def test_base_order_init():
    """测试订单初始化"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000, OrderType.MARKET)
    assert order.ts_code == '000001.SZ'
    assert order.side == OrderSide.BUY
    assert order.quantity == 1000
    assert order.filled_quantity == 0
    assert order.status == OrderStatus.PENDING
    assert order.is_buy()
    assert not order.is_sell()


def test_buy_order_properties():
    """测试买单属性"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    assert order.is_buy() is True
    assert order.is_sell() is False


def test_sell_order_properties():
    """测试卖单属性"""
    order = ConcreteOrder('000001.SZ', OrderSide.SELL, 1000)
    assert order.is_buy() is False
    assert order.is_sell() is True


def test_remaining_quantity():
    """测试剩余数量计算"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    assert order.get_remaining_quantity() == 1000
    order.filled_quantity = 300
    assert order.get_remaining_quantity() == 700


def test_can_cancel():
    """测试可取消状态判断"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    assert order.can_cancel() is True  # PENDING

    order.submit()
    assert order.can_cancel() is True  # SUBMITTED

    order.fill(500, 10.0, datetime.now())
    assert order.can_cancel() is True  # PARTIAL

    order.fill(500, 10.0, datetime.now())
    assert order.can_cancel() is False  # FILLED

    order.cancel()
    assert order.can_cancel() is False  # CANCELLED


def test_full_fill():
    """测试完全成交"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    assert not order.is_filled()
    order.fill(1000, 10.5, datetime.now())
    assert order.is_filled()
    assert order.filled_quantity == 1000
    assert order.filled_avg_price == 10.5
    assert order.filled_at is not None


def test_partial_fill():
    """测试部分成交"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    order.fill(400, 10.0, datetime.now())
    assert order.is_partial_filled()
    assert not order.is_filled()
    assert order.filled_quantity == 400
    assert order.filled_avg_price == 10.0


def test_average_price_calculation():
    """测试平均成交价计算"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    order.fill(500, 10.0, datetime.now())
    assert order.filled_avg_price == 10.0
    order.fill(500, 11.0, datetime.now())
    # (500*10 + 500*11)/1000 = 10.5
    assert order.filled_avg_price == 10.5


def test_submit_transition():
    """测试提交状态转换"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    assert order.status == OrderStatus.PENDING
    order.submit()
    assert order.status == OrderStatus.SUBMITTED
    assert order.submitted_at is not None


def test_cancel_transition():
    """测试取消状态转换"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    order.submit()
    order.cancel()
    assert order.status == OrderStatus.CANCELLED


def test_reject_transition():
    """测试拒绝状态转换"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    order.reject()
    assert order.status == OrderStatus.REJECTED


def test_can_trigger_stop_buy():
    """测试买入止损单触发条件"""
    # 买入止损：价格上涨到止损价触发
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000, OrderType.STOP, stop_price=10.5)
    assert not order.can_trigger(10.0)
    assert order.can_trigger(11.0)


def test_can_trigger_stop_sell():
    """测试卖出止损单触发条件"""
    # 卖出止损：价格下跌到止损价触发
    order = ConcreteOrder('000001.SZ', OrderSide.SELL, 1000, OrderType.STOP, stop_price=10.0)
    assert not order.can_trigger(10.5)
    assert order.can_trigger(9.5)


def test_notional_calculation():
    """测试名义价值计算"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000, OrderType.LIMIT, price=10.0)
    assert order.get_notional() == 10000.0


def test_filled_notional_calculation():
    """测试成交名义价值计算"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000)
    order.fill(500, 10.0, datetime.now())
    assert order.get_filled_notional() == 5000.0


def test_to_dict():
    """测试转换为字典"""
    order = ConcreteOrder('000001.SZ', OrderSide.BUY, 1000, OrderType.MARKET)
    d = order.to_dict()
    assert d['ts_code'] == '000001.SZ'
    assert d['side'] == 'BUY'
    assert d['quantity'] == 1000
