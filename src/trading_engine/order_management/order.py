"""
具体订单实现类
支持多种订单类型：市价单、限价单、止损单、止损限价单
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.trading_engine.base.base_order import BaseOrder, OrderSide, OrderStatus, OrderType


class Order(BaseOrder):
    """标准订单实现类"""

    def __init__(
        self,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy_id: Optional[str] = None,
    ):
        """
        创建订单
        Args:
            ts_code: 股票代码
            side: 买卖方向
            quantity: 委托数量
            order_type: 订单类型
            price: 限价（限价单/止损限价单需要）
            stop_price: 触发价（止损单/止损限价单需要）
            strategy_id: 策略ID
        """
        super().__init__(ts_code, side, quantity, order_type, price, stop_price, strategy_id)
        # 生成唯一订单ID
        self.order_id = self._generate_order_id()

    def _generate_order_id(self) -> str:
        """生成唯一订单ID"""
        return str(uuid.uuid4())[:8]

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
        """检查是否可以取消"""
        cancellable_states = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL,
        ]
        return self.status in cancellable_states

    def fill(self, filled_quantity: int, filled_price: float, filled_time: datetime) -> None:
        """处理成交"""
        if filled_quantity <= 0:
            return

        # 更新成交数量和均价
        if self.filled_avg_price is None:
            self.filled_avg_price = filled_price
        else:
            total_value = self.filled_avg_price * self.filled_quantity + filled_price * filled_quantity
            self.filled_avg_price = total_value / (self.filled_quantity + filled_quantity)

        self.filled_quantity += filled_quantity
        self.updated_at = filled_time

        # 更新状态
        if self.filled_quantity >= self.quantity:
            # 完全成交
            self.status = OrderStatus.FILLED
            self.filled_at = filled_time
        else:
            # 部分成交
            self.status = OrderStatus.PARTIAL

    def cancel(self) -> None:
        """取消订单"""
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now()

    def reject(self) -> None:
        """拒绝订单"""
        self.status = OrderStatus.REJECTED
        self.updated_at = datetime.now()

    def submit(self) -> None:
        """提交订单"""
        self.status = OrderStatus.SUBMITTED
        self.submitted_at = datetime.now()
        self.updated_at = datetime.now()

    def can_trigger(self, current_price: float) -> bool:
        """检查止损单是否满足触发条件"""
        if self.order_type not in [OrderType.STOP, OrderType.STOP_LIMIT]:
            return False
        if self.stop_price is None:
            return False

        # 买入止损：价格上涨到触发价时触发
        if self.is_buy():
            return current_price >= self.stop_price
        # 卖出止损：价格下跌到触发价时触发
        else:
            return current_price <= self.stop_price

    def get_notional(self) -> float:
        """获取委托名义价值"""
        if self.price is not None:
            return self.quantity * self.price
        if self.filled_avg_price is not None:
            return self.quantity * self.filled_avg_price
        return 0.0

    def get_filled_notional(self) -> float:
        """获取已成交名义价值"""
        if self.filled_avg_price is None:
            return 0.0
        return self.filled_quantity * self.filled_avg_price

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "ts_code": self.ts_code,
            "side": self.side.name,
            "side_code": self.side.value,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.get_remaining_quantity(),
            "order_type": self.order_type.name,
            "order_type_code": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "filled_avg_price": self.filled_avg_price,
            "status": self.status.name,
            "status_code": self.status.value,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "commission": self.commission,
            "slippage": self.slippage,
            "notional": self.get_notional(),
            "filled_notional": self.get_filled_notional(),
            "extra_info": self.extra_info,
        }

    @classmethod
    def create_market_order(
        cls,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        strategy_id: Optional[str] = None,
    ) -> "Order":
        """创建市价单"""
        return cls(ts_code, side, quantity, OrderType.MARKET, strategy_id=strategy_id)

    @classmethod
    def create_limit_order(
        cls,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        price: float,
        strategy_id: Optional[str] = None,
    ) -> "Order":
        """创建限价单"""
        return cls(
            ts_code=ts_code,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=price,
            strategy_id=strategy_id,
        )

    @classmethod
    def create_stop_order(
        cls,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        stop_price: float,
        strategy_id: Optional[str] = None,
    ) -> "Order":
        """创建止损单"""
        return cls(
            ts_code=ts_code,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP,
            stop_price=stop_price,
            strategy_id=strategy_id,
        )

    @classmethod
    def create_stop_limit_order(
        cls,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        stop_price: float,
        limit_price: float,
        strategy_id: Optional[str] = None,
    ) -> "Order":
        """创建止损限价单"""
        return cls(
            ts_code=ts_code,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP_LIMIT,
            price=limit_price,
            stop_price=stop_price,
            strategy_id=strategy_id,
        )


# 便捷别名
MarketOrder = Order.create_market_order
LimitOrder = Order.create_limit_order
StopOrder = Order.create_stop_order
StopLimitOrder = Order.create_stop_limit_order
