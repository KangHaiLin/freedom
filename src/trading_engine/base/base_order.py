"""
订单抽象基类
定义订单的通用接口和基础属性
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class OrderSide(Enum):
    """订单方向枚举"""

    BUY = 1
    SELL = 2
    HOLD = 3


class OrderType(Enum):
    """订单类型枚举"""

    MARKET = 1  # 市价单
    LIMIT = 2  # 限价单
    STOP = 3  # 止损单
    STOP_LIMIT = 4  # 止损限价单


class OrderStatus(Enum):
    """订单状态枚举"""

    PENDING = 1  # 待处理
    SUBMITTED = 2  # 已提交
    PARTIAL = 3  # 部分成交
    FILLED = 4  # 完全成交
    CANCELLED = 5  # 已取消
    REJECTED = 6  # 已拒绝
    EXPIRED = 7  # 已过期


class BaseOrder(ABC):
    """订单抽象基类"""

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
        初始化订单
        Args:
            ts_code: 股票代码
            side: 订单方向（买/卖）
            quantity: 订单数量（股）
            order_type: 订单类型
            price: 限价价格（限价单需要）
            stop_price: 触发价格（止损单需要）
            strategy_id: 策略ID
        """
        self.order_id: str = ""  # 订单ID，由分配器生成
        self.ts_code: str = ts_code
        self.side: OrderSide = side
        self.quantity: int = quantity
        self.filled_quantity: int = 0  # 已成交数量
        self.order_type: OrderType = order_type
        self.price: Optional[float] = price
        self.stop_price: Optional[float] = stop_price
        self.strategy_id: Optional[str] = strategy_id

        self.status: OrderStatus = OrderStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.submitted_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.filled_at: Optional[datetime] = None

        self.commission: float = 0.0  # 佣金
        self.slippage: float = 0.0  # 滑点
        self.filled_avg_price: Optional[float] = None  # 成交均价

        self.extra_info: Dict[str, Any] = {}  # 扩展信息

    @abstractmethod
    def is_buy(self) -> bool:
        """是否是买单"""
        pass

    @abstractmethod
    def is_sell(self) -> bool:
        """是否是卖单"""
        pass

    @abstractmethod
    def get_remaining_quantity(self) -> int:
        """获取剩余未成交数量"""
        pass

    @abstractmethod
    def is_filled(self) -> bool:
        """是否完全成交"""
        pass

    @abstractmethod
    def is_partial_filled(self) -> bool:
        """是否部分成交"""
        pass

    @abstractmethod
    def can_cancel(self) -> bool:
        """是否可以取消"""
        pass

    @abstractmethod
    def fill(self, filled_quantity: int, filled_price: float, filled_time: datetime) -> None:
        """
        成交处理
        Args:
            filled_quantity: 本次成交数量
            filled_price: 成交价格
            filled_time: 成交时间
        """
        pass

    @abstractmethod
    def cancel(self) -> None:
        """取消订单"""
        pass

    @abstractmethod
    def reject(self) -> None:
        """拒绝订单"""
        pass

    @abstractmethod
    def submit(self) -> None:
        """提交订单"""
        pass

    @abstractmethod
    def can_trigger(self, current_price: float) -> bool:
        """
        检查是否可以触发（止损单/条件单）
        Args:
            current_price: 当前价格
        Returns:
            是否可以触发
        """
        pass

    @abstractmethod
    def get_notional(self) -> float:
        """获取订单名义价值（数量 * 价格）"""
        pass

    @abstractmethod
    def get_filled_notional(self) -> float:
        """获取已成交名义价值"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass

    def update_status(self, status: OrderStatus) -> None:
        """更新订单状态"""
        self.status = status
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"BaseOrder(order_id={self.order_id}, ts_code={self.ts_code}, "
            f"side={self.side.name}, quantity={self.quantity}, "
            f"filled={self.filled_quantity}, status={self.status.name})"
        )
