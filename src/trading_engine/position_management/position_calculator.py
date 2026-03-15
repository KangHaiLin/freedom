"""
持仓计算器
提供投资组合层面的市值、盈亏、权重计算
"""
from typing import Dict, List, Optional
from src.trading_engine.position_management.position import Position


class PositionCalculator:
    """持仓计算器，提供投资组合统计计算"""

    @staticmethod
    def calculate_total_market_value(positions: Dict[str, Position]) -> float:
        """
        计算总市值
        Args:
            positions: 持仓字典 {ts_code: Position}
        Returns:
            总市值
        """
        total = 0.0
        for pos in positions.values():
            total += pos.get_market_value()
        return total

    @staticmethod
    def calculate_total_cost(positions: Dict[str, Position]) -> float:
        """
        计算总成本
        Args:
            positions: 持仓字典
        Returns:
            总成本
        """
        total = 0.0
        for pos in positions.values():
            total += pos.get_cost()
        return total

    @staticmethod
    def calculate_total_unrealized_pnl(positions: Dict[str, Position]) -> float:
        """
        计算总未实现盈亏
        Args:
            positions: 持仓字典
        Returns:
            总未实现盈亏
        """
        total = 0.0
        for pos in positions.values():
            total += pos.get_unrealized_pnl()
        return total

    @staticmethod
    def calculate_total_realized_pnl(positions: Dict[str, Position]) -> float:
        """
        计算总已实现盈亏
        Args:
            positions: 持仓字典
        Returns:
            总已实现盈亏
        """
        total = 0.0
        for pos in positions.values():
            total += pos.get_realized_pnl()
        return total

    @staticmethod
    def calculate_weights(positions: Dict[str, Position], total_market_value: Optional[float] = None) -> Dict[str, float]:
        """
        计算各持仓权重
        Args:
            positions: 持仓字典
            total_market_value: 总市值，如果为None会自动计算
        Returns:
            权重字典 {ts_code: weight}，总和为1
        """
        if total_market_value is None:
            total_market_value = PositionCalculator.calculate_total_market_value(positions)

        if total_market_value <= 0:
            return {ts_code: 0.0 for ts_code in positions}

        weights = {}
        for ts_code, pos in positions.items():
            mv = pos.get_market_value()
            weights[ts_code] = mv / total_market_value
        return weights

    @staticmethod
    def calculate_portfolio_pnl_percentage(
        positions: Dict[str, Position],
        total_cash: float = 0.0
    ) -> float:
        """
        计算投资组合整体收益率
        Args:
            positions: 持仓字典
            total_cash: 可用现金
        Returns:
            收益率 (总盈亏 / 总成本)
        """
        total_cost = PositionCalculator.calculate_total_cost(positions) + total_cash
        if total_cost <= 0:
            return 0.0
        total_unrealized = PositionCalculator.calculate_total_unrealized_pnl(positions)
        total_realized = PositionCalculator.calculate_total_realized_pnl(positions)
        total_pnl = total_unrealized + total_realized
        return total_pnl / total_cost

    @staticmethod
    def get_non_empty_positions(positions: Dict[str, Position]) -> List[Position]:
        """
        获取所有非空持仓
        Args:
            positions: 持仓字典
        Returns:
            非空持仓列表
        """
        return [pos for pos in positions.values() if not pos.is_empty()]

    @staticmethod
    def calculate_portfolio_summary(
        positions: Dict[str, Position],
        cash: float = 0.0
    ) -> Dict[str, float]:
        """
        计算投资组合汇总统计
        Args:
            positions: 持仓字典
            cash: 可用现金
        Returns:
            统计字典
        """
        non_empty = PositionCalculator.get_non_empty_positions(positions)
        total_market_value = PositionCalculator.calculate_total_market_value(positions)
        total_cost = PositionCalculator.calculate_total_cost(positions)
        total_unrealized_pnl = PositionCalculator.calculate_total_unrealized_pnl(positions)
        total_realized_pnl = PositionCalculator.calculate_total_realized_pnl(positions)
        total_asset = total_market_value + cash
        pnl_pct = PositionCalculator.calculate_portfolio_pnl_percentage(positions, cash)
        weights = PositionCalculator.calculate_weights(positions, total_market_value)

        return {
            'position_count': len(non_empty),
            'total_market_value': total_market_value,
            'total_cost': total_cost,
            'cash': cash,
            'total_asset': total_asset,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_unrealized_pnl + total_realized_pnl,
            'pnl_percentage': pnl_pct * 100,  # 转百分比
            'unrealized_pnl_percentage': (total_unrealized_pnl / (total_cost + cash) * 100) if total_cost + cash > 0 else 0,
            'weights': weights,
        }

    @staticmethod
    def calculate_position_count(positions: Dict[str, Position]) -> int:
        """
        计算非空持仓数量
        Args:
            positions: 持仓字典
        Returns:
            非空持仓数量
        """
        return len(PositionCalculator.get_non_empty_positions(positions))
