"""
投资组合管理器
管理多个股票持仓，提供整体统计查询
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.trading_engine.order_management.order import Order
from src.trading_engine.position_management.position import Position
from src.trading_engine.position_management.position_calculator import PositionCalculator

logger = logging.getLogger(__name__)


class PortfolioManager:
    """投资组合管理器，统一管理所有持仓"""

    def __init__(self, initial_cash: float = 0.0):
        """
        初始化投资组合
        Args:
            initial_cash: 初始可用资金
        """
        self._positions: Dict[str, Position] = {}
        self._cash: float = initial_cash
        self._initial_cash: float = initial_cash
        self._calculator = PositionCalculator()

    def get_position(self, ts_code: str) -> Optional[Position]:
        """
        获取指定股票持仓
        Args:
            ts_code: 股票代码
        Returns:
            持仓对象，不存在返回None
        """
        return self._positions.get(ts_code)

    def get_or_create_position(self, ts_code: str) -> Position:
        """
        获取持仓，如果不存在则创建空持仓
        Args:
            ts_code: 股票代码
        Returns:
            持仓对象
        """
        if ts_code not in self._positions:
            self._positions[ts_code] = Position(ts_code, 0, 0.0)
        return self._positions[ts_code]

    def add_position(self, ts_code: str, quantity: int, price: float, commission: float = 0.0) -> Tuple[float, float]:
        """
        增加持仓（买入成交后调用）
        Args:
            ts_code: 股票代码
            quantity: 买入数量
            price: 成交价格
            commission: 佣金
        Returns:
            (新平均成本, 总花费金额)
        """
        position = self.get_or_create_position(ts_code)
        total_cost = quantity * price + commission
        # 扣除现金
        self._cash -= total_cost
        # 更新持仓
        new_avg_cost = position.add_position(quantity, price, commission)
        logger.debug(
            f"增加持仓: {ts_code}, 数量: {quantity}, 价格: {price:.4f}, "
            f"佣金: {commission:.4f}, 新平均成本: {new_avg_cost:.4f}"
        )
        return new_avg_cost, total_cost

    def reduce_position(
        self, ts_code: str, quantity: int, price: float, commission: float = 0.0
    ) -> Tuple[float, float]:
        """
        减少持仓（卖出成交后调用）
        Args:
            ts_code: 股票代码
            quantity: 卖出数量
            price: 成交价格
            commission: 佣金
        Returns:
            (本次实现盈亏, 总收入金额)
        """
        position = self.get_position(ts_code)
        if position is None:
            logger.warning(f"尝试减少不存在的持仓: {ts_code}")
            return 0.0, 0.0

        if position.quantity < quantity:
            logger.warning(f"持仓不足: {ts_code} 需卖出 {quantity}, 持仓 {position.quantity}")
            quantity = position.quantity

        pnl = position.reduce_position(quantity, price, commission)
        total_amount = quantity * price - commission
        self._cash += total_amount
        logger.debug(
            f"减少持仓: {ts_code}, 数量: {quantity}, 价格: {price:.4f}, " f"佣金: {commission:.4f}, 实现盈亏: {pnl:.4f}"
        )
        return pnl, total_amount

    def close_position(self, ts_code: str, price: float, commission: float = 0.0) -> Tuple[float, float]:
        """
        平仓全部持仓
        Args:
            ts_code: 股票代码
            price: 成交价格
            commission: 佣金
        Returns:
            (总实现盈亏, 总收入金额)
        """
        position = self.get_position(ts_code)
        if position is None or position.is_empty():
            logger.warning(f"尝试平空空持仓: {ts_code}")
            return 0.0, 0.0

        quantity = position.quantity
        pnl = position.close_position(price, commission)
        total_amount = quantity * price - commission
        self._cash += total_amount
        logger.debug(
            f"平仓持仓: {ts_code}, 数量: {quantity}, 价格: {price:.4f}, " f"佣金: {commission:.4f}, 总盈亏: {pnl:.4f}"
        )
        return pnl, total_amount

    def process_order_fill(
        self, order: Order, filled_quantity: int, filled_price: float, commission: float = 0.0
    ) -> float:
        """
        处理订单成交，更新持仓和现金
        Args:
            order: 订单对象
            filled_quantity: 成交数量
            filled_price: 成交价格
            commission: 佣金
        Returns:
            盈亏（买入返回总花费，卖出返回盈亏）
        """
        ts_code = order.ts_code
        if order.is_buy():
            _, cost = self.add_position(ts_code, filled_quantity, filled_price, commission)
            return -cost  # 买入是支出，返回负
        else:
            pnl, _ = self.reduce_position(ts_code, filled_quantity, filled_price, commission)
            return pnl

    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        批量更新最新价格
        Args:
            prices: {ts_code: price} 价格字典
        """
        for ts_code, price in prices.items():
            position = self.get_position(ts_code)
            if position is not None:
                position.update_price(price)

    def update_price(self, ts_code: str, price: float) -> None:
        """
        更新单个股票最新价格
        Args:
            ts_code: 股票代码
            price: 最新价格
        """
        position = self.get_position(ts_code)
        if position is not None:
            position.update_price(price)

    def get_cash(self) -> float:
        """获取当前可用现金"""
        return self._cash

    def set_cash(self, cash: float) -> None:
        """设置现金"""
        self._cash = cash

    def get_initial_cash(self) -> float:
        """获取初始现金"""
        return self._initial_cash

    def get_total_asset(self) -> float:
        """获取总资产 = 总市值 + 现金"""
        total_mv = self._calculator.calculate_total_market_value(self._positions)
        return total_mv + self._cash

    def get_summary(self) -> Dict[str, float]:
        """获取投资组合汇总统计"""
        return self._calculator.calculate_portfolio_summary(self._positions, self._cash)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self._positions

    def get_non_empty_positions(self) -> List[Position]:
        """获取所有非空持仓"""
        return self._calculator.get_non_empty_positions(self._positions)

    def get_position_count(self) -> int:
        """获取非空持仓数量"""
        return self._calculator.calculate_position_count(self._positions)

    def check_buy_available(self, price: float, quantity: int, commission_rate: float = 0.0003) -> bool:
        """
        检查是否有足够资金买入
        Args:
            price: 价格
            quantity: 数量
            commission_rate: 佣金费率
        Returns:
            是否有足够资金
        """
        required = price * quantity * (1 + commission_rate)
        return self._cash >= required

    def check_sell_available(self, ts_code: str, quantity: int) -> bool:
        """
        检查是否有足够持仓卖出
        Args:
            ts_code: 股票代码
            quantity: 要卖出的数量
        Returns:
            是否有足够持仓
        """
        position = self.get_position(ts_code)
        if position is None:
            return False
        return position.quantity >= quantity

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        summary = self.get_summary()
        positions_dict = {ts_code: pos.to_dict() for ts_code, pos in self._positions.items() if not pos.is_empty()}
        return {
            "initial_cash": self._initial_cash,
            "current_cash": self._cash,
            "total_asset": self.get_total_asset(),
            "summary": summary,
            "positions": positions_dict,
            "position_count": self.get_position_count(),
        }

    def clear_all(self) -> None:
        """清空所有持仓"""
        self._positions.clear()
        logger.debug("清空所有持仓")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "cash": self._cash,
            "initial_cash": self._initial_cash,
            "position_count": len(self._positions),
        }
