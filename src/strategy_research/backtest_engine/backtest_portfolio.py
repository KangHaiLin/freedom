"""
回测投资组合
管理现金、持仓、成交记录
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.strategy_research.base import PositionSnapshot, TradeDirection, TradeRecord

from .backtest_config import BacktestConfig


@dataclass
class Position:
    """单个持仓"""

    ts_code: str
    quantity: int = 0
    avg_cost: float = 0.0

    @property
    def market_value(self, current_price: float) -> float:
        return self.quantity * current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost


class BacktestPortfolio:
    """回测投资组合"""

    def __init__(self, config: BacktestConfig):
        self._config = config
        self._cash = config.initial_capital
        self._positions: Dict[str, Position] = {}
        self._total_commission = 0.0

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def total_commission(self) -> float:
        return self._total_commission

    def get_position(self, ts_code: str) -> Position:
        """获取持仓，如果不存在返回零持仓"""
        if ts_code not in self._positions:
            return Position(ts_code=ts_code, quantity=0, avg_cost=0.0)
        return self._positions[ts_code]

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self._positions

    def market_value(self, current_prices: Dict[str, float]) -> float:
        """计算当前总市值"""
        total = 0.0
        for ts_code, pos in self._positions.items():
            if ts_code in current_prices:
                total += pos.quantity * current_prices[ts_code]
        return total

    def total_assets(self, current_prices: Dict[str, float]) -> float:
        """计算总资产 = 现金 + 市值"""
        return self._cash + self.market_value(current_prices)

    def calculate_commission(self, amount: float) -> float:
        """计算佣金"""
        commission = amount * self._config.commission_rate
        return max(commission, self._config.min_commission)

    def apply_slippage(self, price: float, direction: TradeDirection) -> float:
        """应用滑点"""
        if direction == TradeDirection.BUY:
            # 买入价格上浮
            return price * (1 + self._config.slippage)
        else:
            # 卖出价格下浮
            return price * (1 - self._config.slippage)

    def buy(
        self,
        ts_code: str,
        price: float,
        quantity: int,
        direction: TradeDirection = TradeDirection.BUY,
    ) -> TradeRecord:
        """买入"""
        # 应用滑点
        executed_price = self.apply_slippage(price, direction)
        amount = executed_price * quantity
        commission = self.calculate_commission(amount)

        # 扣减现金和佣金
        self._cash -= amount + commission
        self._total_commission += commission

        # 更新持仓
        if ts_code in self._positions:
            pos = self._positions[ts_code]
            # 平均成本加权
            new_quantity = pos.quantity + quantity
            if new_quantity > 0:
                new_avg_cost = (pos.avg_cost * pos.quantity + amount) / new_quantity
            else:
                new_avg_cost = 0
            pos.quantity = new_quantity
            pos.avg_cost = new_avg_cost
            if pos.quantity == 0:
                del self._positions[ts_code]
        else:
            self._positions[ts_code] = Position(
                ts_code=ts_code,
                quantity=quantity,
                avg_cost=executed_price,
            )

        # 创建交易记录
        position_before = self.get_position(ts_code).quantity - quantity
        position_after = self.get_position(ts_code).quantity

        return TradeRecord(
            trade_id=0,  # will be filled by backtest engine
            ts_code=ts_code,
            direction=direction,
            quantity=quantity,
            price=executed_price,
            amount=amount,
            commission=commission,
            trade_date=None,  # will be filled by backtest engine
            position_before=position_before,
            position_after=position_after,
        )

    def sell(
        self,
        ts_code: str,
        price: float,
        quantity: int,
        direction: TradeDirection = TradeDirection.SELL,
    ) -> TradeRecord:
        """卖出"""
        # 应用滑点
        executed_price = self.apply_slippage(price, direction)
        amount = executed_price * quantity
        commission = self.calculate_commission(amount)

        # 计算盈亏
        pos = self.get_position(ts_code)
        pnl = (executed_price - pos.avg_cost) * quantity

        # 增加现金（减去佣金）
        self._cash += amount - commission
        self._total_commission += commission

        # 更新持仓
        pos.quantity -= quantity
        if pos.quantity <= 0:
            if ts_code in self._positions:
                del self._positions[ts_code]
        else:
            self._positions[ts_code] = pos

        position_before = pos.quantity + quantity
        position_after = self.get_position(ts_code).quantity if ts_code in self._positions else 0

        return TradeRecord(
            trade_id=0,  # will be filled by backtest engine
            ts_code=ts_code,
            direction=direction,
            quantity=quantity,
            price=executed_price,
            amount=amount,
            commission=commission,
            trade_date=None,  # will be filled by backtest engine
            position_before=position_before,
            position_after=position_after,
            pnl=pnl,
            pnl_pct=pnl / (pos.avg_cost * quantity) if pos.avg_cost * quantity > 0 else 0,
        )

    def get_snapshot(self, current_prices: Dict[str, float]) -> Dict[str, PositionSnapshot]:
        """获取持仓快照"""
        snapshots = {}
        for ts_code, pos in self._positions.items():
            current_price = current_prices.get(ts_code, pos.avg_cost)
            market_value = pos.quantity * current_price
            cost_basis = pos.quantity * pos.avg_cost
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = unrealized_pnl / cost_basis if cost_basis > 0 else 0
            snapshots[ts_code] = PositionSnapshot(
                ts_code=ts_code,
                quantity=pos.quantity,
                avg_cost=pos.avg_cost,
                current_price=current_price,
                market_value=market_value,
                cost_basis=cost_basis,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
        return snapshots

    def close_all(self, current_prices: Dict[str, float]) -> List[TradeRecord]:
        """平仓所有持仓"""
        trades = []
        positions = list(self._positions.values())
        for pos in positions:
            if pos.quantity > 0:
                trade = self.sell(pos.ts_code, current_prices.get(pos.ts_code, pos.avg_cost), pos.quantity)
                trades.append(trade)
        return trades

    def count_positions(self) -> int:
        """当前持仓数量"""
        return len([p for p in self._positions.values() if p.quantity > 0])
