"""
Unit tests for base_position.py
"""

from datetime import datetime

import pytest

from src.trading_engine.base.base_position import BasePosition


class ConcretePosition(BasePosition):
    """具体实现用于测试抽象基类"""

    def is_empty(self) -> bool:
        return self.quantity == 0

    def get_market_value(self) -> float:
        if self.last_price is None:
            return 0.0
        return self.quantity * self.last_price

    def get_cost(self) -> float:
        return self.quantity * self.avg_cost

    def get_unrealized_pnl(self) -> float:
        if self.last_price is None:
            return 0.0
        return (self.last_price - self.avg_cost) * self.quantity

    def get_unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        if self.last_price is None:
            return 0.0
        return (self.last_price - self.avg_cost) / self.avg_cost

    def get_realized_pnl(self) -> float:
        return self.realized_pnl

    def update_price(self, current_price: float) -> None:
        self.last_price = current_price
        self.last_update_time = datetime.now()
        self.unrealized_pnl = self.get_unrealized_pnl()

    def add_position(self, quantity: int, price: float, commission: float = 0.0) -> float:
        total_cost = self.quantity * self.avg_cost + quantity * price + commission
        self.quantity += quantity
        self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0.0
        self.total_bought += quantity
        self.total_bought_amount += quantity * price + commission
        return self.avg_cost

    def reduce_position(self, quantity: int, price: float, commission: float = 0.0) -> float:
        # 计算本次实现盈亏
        pnl = (price - self.avg_cost) * quantity - commission
        self.realized_pnl += pnl
        self.quantity -= quantity
        self.total_sold += quantity
        self.total_sold_amount += quantity * price - commission
        return pnl

    def close_position(self, price: float, commission: float = 0.0) -> float:
        quantity = self.quantity
        if quantity == 0:
            return 0.0
        pnl = (price - self.avg_cost) * quantity - commission
        self.realized_pnl += pnl
        self.total_sold += quantity
        self.total_sold_amount += quantity * price - commission
        self.quantity = 0
        return self.realized_pnl

    def to_dict(self) -> dict:
        return {
            "ts_code": self.ts_code,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "last_price": self.last_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
        }


def test_position_init():
    """测试持仓初始化"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    assert pos.ts_code == "000001.SZ"
    assert pos.quantity == 1000
    assert pos.avg_cost == 10.0
    assert pos.is_empty() is False


def test_empty_position():
    """测试空持仓"""
    pos = ConcretePosition("000001.SZ", 0, 0.0)
    assert pos.is_empty() is True


def test_update_price():
    """测试更新价格"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    assert pos.last_price == 12.0
    assert pos.last_update_time is not None


def test_get_market_value():
    """测试市值计算"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    assert pos.get_market_value() == 0.0
    pos.update_price(12.0)
    assert pos.get_market_value() == 12000.0


def test_get_unrealized_pnl():
    """测试未实现盈亏计算"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    # (12 - 10) * 1000 = 2000
    assert pos.get_unrealized_pnl() == 2000.0
    assert pos.unrealized_pnl == 2000.0


def test_get_unrealized_pnl_pct():
    """测试未实现盈亏百分比计算"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    pos.update_price(12.0)
    # (12 - 10) / 10 = 0.2 = 20%
    assert pos.get_unrealized_pnl_pct() == 0.2


def test_add_position():
    """测试增加持仓"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    # 加仓500，价格11.0
    new_avg = pos.add_position(500, 11.0)
    # (1000*10 + 500*11) / 1500 = 15500 / 1500 = 10.333...
    assert pos.quantity == 1500
    assert abs(new_avg - 10.3333) < 0.001
    assert pos.total_bought == 500


def test_add_position_with_commission():
    """测试增加持仓带佣金"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    # 佣金5元
    new_avg = pos.add_position(500, 11.0, commission=5.0)
    total_cost = 1000 * 10 + 500 * 11 + 5
    expected_avg = total_cost / 1500
    assert abs(new_avg - expected_avg) < 0.001


def test_reduce_position():
    """测试减少持仓"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    # 卖出500，价格12.0，佣金5元
    pnl = pos.reduce_position(500, 12.0, commission=5.0)
    # (12 - 10)*500 - 5 = 1000 - 5 = 995
    assert abs(pnl - 995) < 0.001
    assert pos.quantity == 500
    assert pos.realized_pnl == 995
    assert pos.total_sold == 500


def test_close_position():
    """测试平仓"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    # 全部卖出，价格12.0
    total_pnl = pos.close_position(12.0)
    # (12 - 10)*1000 = 2000
    assert abs(total_pnl - 2000) < 0.001
    assert pos.quantity == 0
    assert pos.is_empty()
    assert pos.realized_pnl == 2000


def test_close_empty_position():
    """测试空持仓平仓"""
    pos = ConcretePosition("000001.SZ", 0, 0.0)
    pnl = pos.close_position(10.0)
    assert pnl == 0.0


def test_to_dict():
    """测试转换为字典"""
    pos = ConcretePosition("000001.SZ", 1000, 10.0)
    d = pos.to_dict()
    assert d["ts_code"] == "000001.SZ"
    assert d["quantity"] == 1000
    assert d["avg_cost"] == 10.0
