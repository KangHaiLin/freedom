"""
持仓抽象基类
定义持仓的通用接口和基础属性
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any


class BasePosition(ABC):
    """持仓抽象基类"""

    def __init__(
        self,
        ts_code: str,
        quantity: int = 0,
        avg_cost: float = 0.0
    ):
        """
        初始化持仓
        Args:
            ts_code: 股票代码
            quantity: 持仓数量
            avg_cost: 平均成本价
        """
        self.ts_code: str = ts_code
        self.quantity: int = quantity
        self.avg_cost: float = avg_cost
        self.last_price: Optional[float] = None
        self.last_update_time: Optional[datetime] = None

        # 统计信息
        self.total_bought: int = 0  # 累计买入数量
        self.total_sold: int = 0  # 累计卖出数量
        self.total_bought_amount: float = 0.0  # 累计买入金额
        self.total_sold_amount: float = 0.0  # 累计卖出金额
        self.realized_pnl: float = 0.0  # 已实现盈亏
        self.unrealized_pnl: float = 0.0  # 未实现盈亏

        self.created_at: datetime = datetime.now()
        self.extra_info: Dict[str, Any] = {}

    @abstractmethod
    def is_empty(self) -> bool:
        """持仓是否为空"""
        pass

    @abstractmethod
    def get_market_value(self) -> float:
        """获取当前市值"""
        pass

    @abstractmethod
    def get_cost(self) -> float:
        """获取持仓成本"""
        pass

    @abstractmethod
    def get_unrealized_pnl(self) -> float:
        """获取未实现盈亏"""
        pass

    @abstractmethod
    def get_unrealized_pnl_pct(self) -> float:
        """获取未实现盈亏百分比"""
        pass

    @abstractmethod
    def get_realized_pnl(self) -> float:
        """获取已实现盈亏"""
        pass

    @abstractmethod
    def update_price(self, current_price: float) -> None:
        """
        更新最新价格
        Args:
            current_price: 当前价格
        """
        pass

    @abstractmethod
    def add_position(self, quantity: int, price: float, commission: float = 0.0) -> float:
        """
        增加持仓（买入成交）
        Args:
            quantity: 增加数量
            price: 成交价格
            commission: 佣金
        Returns:
            新的平均成本价
        """
        pass

    @abstractmethod
    def reduce_position(self, quantity: int, price: float, commission: float = 0.0) -> float:
        """
        减少持仓（卖出成交）
        Args:
            quantity: 减少数量
            price: 成交价格
            commission: 佣金
        Returns:
            本次实现盈亏
        """
        pass

    @abstractmethod
    def close_position(self, price: float, commission: float = 0.0) -> float:
        """
        平仓全部持仓
        Args:
            price: 成交价格
            commission: 佣金
        Returns:
            最终实现盈亏
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass

    def __repr__(self) -> str:
        return (
            f"BasePosition(ts_code={self.ts_code}, quantity={self.quantity}, "
            f"avg_cost={self.avg_cost:.4f}, unrealized_pnl={self.unrealized_pnl:.4f})"
        )
