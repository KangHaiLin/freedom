"""
持仓实现类
存储单个股票的持仓信息，支持增减仓、盈亏计算
"""

from datetime import datetime
from typing import Any, Dict

from src.trading_engine.base.base_position import BasePosition


class Position(BasePosition):
    """具体持仓实现类"""

    def __init__(self, ts_code: str, quantity: int = 0, avg_cost: float = 0.0):
        """
        初始化持仓
        Args:
            ts_code: 股票代码
            quantity: 初始持仓数量
            avg_cost: 平均成本价
        """
        super().__init__(ts_code, quantity, avg_cost)

    def is_empty(self) -> bool:
        """持仓是否为空"""
        return self.quantity == 0

    def get_market_value(self) -> float:
        """获取当前市值"""
        if self.last_price is None or self.quantity == 0:
            return 0.0
        return self.quantity * self.last_price

    def get_cost(self) -> float:
        """获取持仓成本"""
        return self.quantity * self.avg_cost

    def get_unrealized_pnl(self) -> float:
        """获取未实现盈亏"""
        if self.last_price is None or self.quantity == 0:
            return 0.0
        return (self.last_price - self.avg_cost) * self.quantity

    def get_unrealized_pnl_pct(self) -> float:
        """获取未实现盈亏百分比"""
        if self.avg_cost <= 0 or self.last_price is None:
            return 0.0
        return (self.last_price - self.avg_cost) / self.avg_cost

    def get_realized_pnl(self) -> float:
        """获取已实现盈亏"""
        return self.realized_pnl

    def update_price(self, current_price: float) -> None:
        """更新最新价格"""
        self.last_price = current_price
        self.last_update_time = datetime.now()
        self.unrealized_pnl = self.get_unrealized_pnl()

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
        if quantity <= 0:
            return self.avg_cost

        # 总成本 = 原有成本 + 新增成本 + 佣金
        total_cost = self.quantity * self.avg_cost + quantity * price + commission
        self.quantity += quantity
        self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0.0

        self.total_bought += quantity
        self.total_bought_amount += quantity * price + commission

        return self.avg_cost

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
        if quantity <= 0 or quantity > self.quantity:
            return 0.0

        # 本次盈亏 = (卖出价 - 成本价) * 数量 - 佣金
        pnl = (price - self.avg_cost) * quantity - commission
        self.realized_pnl += pnl

        self.quantity -= quantity
        self.total_sold += quantity
        self.total_sold_amount += quantity * price - commission

        return pnl

    def close_position(self, price: float, commission: float = 0.0) -> float:
        """
        平仓全部持仓
        Args:
            price: 成交价格
            commission: 佣金
        Returns:
            最终实现盈亏
        """
        if self.quantity == 0:
            return 0.0

        quantity = self.quantity
        pnl = (price - self.avg_cost) * quantity - commission
        self.realized_pnl += pnl

        self.total_sold += quantity
        self.total_sold_amount += quantity * price - commission
        self.quantity = 0

        return self.realized_pnl

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "ts_code": self.ts_code,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "last_price": self.last_price,
            "market_value": self.get_market_value(),
            "cost": self.get_cost(),
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.get_unrealized_pnl_pct(),
            "realized_pnl": self.realized_pnl,
            "total_bought": self.total_bought,
            "total_sold": self.total_sold,
            "total_bought_amount": self.total_bought_amount,
            "total_sold_amount": self.total_sold_amount,
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None,
            "created_at": self.created_at.isoformat(),
            "extra_info": self.extra_info,
        }

    def __repr__(self) -> str:
        return (
            f"Position(ts_code={self.ts_code}, quantity={self.quantity}, "
            f"avg_cost={self.avg_cost:.4f}, last_price={self.last_price:.4f}, "
            f"unrealized_pnl={self.unrealized_pnl:.2f})"
        )
