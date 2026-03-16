"""
模拟交易账户
维护账户现金、持仓、权益
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.strategy_research.base import TradeRecord, TradeDirection
from src.strategy_research.base import PositionSnapshot
from .sim_config import SimulationConfig


@dataclass
class SimPosition:
    """模拟持仓"""
    ts_code: str
    quantity: int = 0
    avg_cost: float = 0.0

    @property
    def market_value(self):
        pass  # 需要当前价格计算

    @property
    def cost_basis(self):
        return self.quantity * self.avg_cost


class SimulationAccount:
    """模拟交易账户"""

    def __init__(self, config: SimulationConfig):
        self._config = config
        self._cash = config.initial_capital
        self._positions: Dict[str, SimPosition] = {}
        self._total_commission = 0.0

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def total_commission(self) -> float:
        return self._total_commission

    def get_position(self, ts_code: str) -> SimPosition:
        """获取持仓"""
        if ts_code not in self._positions:
            return SimPosition(ts_code=ts_code, quantity=0, avg_cost=0.0)
        return self._positions[ts_code]

    def get_all_positions(self) -> Dict[str, SimPosition]:
        """获取所有持仓"""
        return self._positions

    def market_value(self, current_prices: Dict[str, float]) -> float:
        """计算当前市值"""
        total = 0.0
        for ts_code, pos in self._positions.items():
            if ts_code in current_prices:
                total += pos.quantity * current_prices[ts_code]
        return total

    def total_assets(self, current_prices: Dict[str, float]) -> float:
        """总资产"""
        return self._cash + self.market_value(current_prices)

    def calculate_commission(self, amount: float) -> float:
        """计算佣金"""
        commission = amount * self._config.commission_rate
        return max(commission, self._config.min_commission)

    def apply_slippage(self, price: float, direction: TradeDirection) -> float:
        """应用滑点"""
        if direction == TradeDirection.BUY:
            return price * (1 + self._config.slippage)
        else:
            return price * (1 - self._config.slippage)

    def buy(
        self,
        ts_code: str,
        price: float,
        quantity: int,
    ) -> TradeRecord:
        """买入"""
        direction = TradeDirection.BUY
        executed_price = self.apply_slippage(price, direction)
        amount = executed_price * quantity
        commission = self.calculate_commission(amount)

        self._cash -= amount + commission
        self._total_commission += commission

        # 更新持仓
        if ts_code in self._positions:
            pos = self._positions[ts_code]
            new_quantity = pos.quantity + quantity
            if new_quantity > 0:
                new_avg = (pos.avg_cost * pos.quantity + amount) / new_quantity
            else:
                new_avg = 0.0
            pos.quantity = new_quantity
            pos.avg_cost = new_avg
            if pos.quantity == 0:
                del self._positions[ts_code]
        else:
            self._positions[ts_code] = SimPosition(
                ts_code=ts_code,
                quantity=quantity,
                avg_cost=executed_price,
            )

        position_before = self.get_position(ts_code).quantity - quantity
        position_after = self.get_position(ts_code).quantity if ts_code in self._positions else 0

        return TradeRecord(
            trade_id=0,
            ts_code=ts_code,
            direction=direction,
            quantity=quantity,
            price=executed_price,
            amount=amount,
            commission=commission,
            trade_date=None,
            position_before=position_before,
            position_after=position_after,
        )

    def sell(
        self,
        ts_code: str,
        price: float,
        quantity: int,
    ) -> TradeRecord:
        """卖出"""
        direction = TradeDirection.SELL
        executed_price = self.apply_slippage(price, direction)
        amount = executed_price * quantity
        commission = self.calculate_commission(amount)

        pos = self.get_position(ts_code)
        pnl = (executed_price - pos.avg_cost) * quantity

        self._cash += amount - commission
        self._total_commission += commission

        pos.quantity -= quantity
        if pos.quantity <= 0:
            if ts_code in self._positions:
                del self._positions[ts_code]
        else:
            self._positions[ts_code] = pos

        position_before = pos.quantity + quantity
        position_after = self.get_position(ts_code).quantity if ts_code in self._positions else 0

        return TradeRecord(
            trade_id=0,
            ts_code=ts_code,
            direction=direction,
            quantity=quantity,
            price=executed_price,
            amount=amount,
            commission=commission,
            trade_date=None,
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

    def count_positions(self) -> int:
        """持仓数量"""
        return len([p for p in self._positions.values() if p.quantity > 0])
