"""
模拟交易引擎
对接实时行情，执行策略信号，维持账户
"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.strategy_research.base import (
    BaseStrategy,
    TradeRecord,
    TradeDirection,
    DailyStats,
)
from .sim_config import SimulationConfig
from .sim_account import SimulationAccount


class SimulationOrder:
    """模拟订单"""
    def __init__(
        self,
        order_id: int,
        ts_code: str,
        direction: TradeDirection,
        price: float,
        quantity: int,
        created_at: datetime,
    ):
        self.order_id = order_id
        self.ts_code = ts_code
        self.direction = direction
        self.price = price
        self.quantity = quantity
        self.created_at = created_at
        self.filled = False
        self.filled_price: Optional[float] = None
        self.filled_quantity: int = 0

    def is_filled(self) -> bool:
        return self.filled


class SimulationEngine:
    """模拟交易引擎"""

    def __init__(
        self,
        strategy: BaseStrategy,
        config: Optional[SimulationConfig] = None,
    ):
        self._strategy = strategy
        self._config = config or SimulationConfig()
        self._account = SimulationAccount(self._config)
        self._orders: List[SimulationOrder] = []
        self._trades: List[TradeRecord] = []
        self._daily_stats: List[DailyStats] = []
        self._trade_id_counter = 1
        self._order_id_counter = 1

        # 初始化策略
        self._strategy.initialize()

    @property
    def account(self) -> SimulationAccount:
        return self._account

    @property
    def trades(self) -> List[TradeRecord]:
        return self._trades

    @property
    def daily_stats(self) -> List[DailyStats]:
        return self._daily_stats

    def place_order(
        self,
        ts_code: str,
        direction: TradeDirection,
        price: float,
        quantity: int,
    ) -> int:
        """
        下单

        Returns:
            订单ID
        """
        if quantity <= 0:
            return -1

        # 检查资金/持仓
        if direction == TradeDirection.BUY:
            required = price * quantity + self._account.calculate_commission(price * quantity)
            if required > self._account.cash:
                # 资金不足，拒绝
                return -1

        order_id = self._order_id_counter
        self._order_id_counter += 1

        order = SimulationOrder(
            order_id=order_id,
            ts_code=ts_code,
            direction=direction,
            price=price,
            quantity=quantity,
            created_at=datetime.now(),
        )
        self._orders.append(order)
        return order_id

    def cancel_order(self, order_id: int) -> bool:
        """撤单"""
        for order in self._orders:
            if order.order_id == order_id and not order.filled:
                order.filled = True  # 标记成交但数量为0
                return True
        return False

    def match_tick(
        self,
        ts_code: str,
        current_price: float,
    ) -> Optional[TradeRecord]:
        """
        对tick数据撮合，当前价格满足市价/限价就成交

        Returns:
            成交记录，如果没有成交返回None
        """
        for order in self._orders:
            if order.filled or order.ts_code != ts_code:
                continue

            # 简化：A股模拟，所有订单当前价格满足就立即全成成交
            if order.direction == TradeDirection.BUY:
                # 买入，当前价格 <= 委托价格 成交（限价单）
                # 市价总是成交
                if order.price <= 0 or current_price <= order.price:
                    return self._fill_order(order, current_price)

            elif order.direction == TradeDirection.SELL:
                # 卖出，当前价格 >= 委托价格 成交
                if order.price <= 0 or current_price >= order.price:
                    return self._fill_order(order, current_price)

        return None

    def match_bar(
        self,
        current_prices: Dict[str, float],
        current_date,
    ) -> List[TradeRecord]:
        """
        日K线撮合，所有未成交订单按收盘价成交

        Returns:
            成交记录列表
        """
        filled_trades = []
        for order in self._orders:
            if order.filled:
                continue
            if order.ts_code not in current_prices:
                continue
            current_price = current_prices[order.ts_code]
            trade = self._fill_order(order, current_price)
            if trade:
                filled_trades.append(trade)
        return filled_trades

    def _fill_order(self, order: SimulationOrder, fill_price: float) -> Optional[TradeRecord]:
        """执行成交"""
        order.filled = True
        order.filled_price = fill_price
        order.filled_quantity = order.quantity

        if order.direction == TradeDirection.BUY:
            trade = self._account.buy(order.ts_code, fill_price, order.quantity)
        else:
            trade = self._account.sell(order.ts_code, fill_price, order.quantity)

        trade.trade_id = self._trade_id_counter
        self._trade_id_counter += 1
        trade.trade_date = datetime.now()

        self._trades.append(trade)
        self._strategy.on_trade(trade, self._account)

        return trade

    def on_bar(
        self,
        bar_data,
        current_date,
        current_prices: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        处理日K线，由策略产生信号，执行信号

        Returns:
            执行结果
        """
        signals = self._strategy.on_bar(bar_data, current_date, self._account)

        # 执行信号
        executed = []
        for ts_code, direction in signals.items():
            if direction == TradeDirection.BUY:
                # 买入全仓能买的数量
                price = current_prices.get(ts_code, 0)
                if price <= 0:
                    continue
                max_quantity = int(self._account.cash // (price * 100)) * 100
                if max_quantity > 0:
                    order_id = self.place_order(ts_code, direction, price, max_quantity)
                    if order_id > 0:
                        executed.append({'order_id': order_id, 'ts_code': ts_code, 'direction': direction})

            elif direction == TradeDirection.SELL:
                # 卖出全部持仓
                pos = self._account.get_position(ts_code)
                if pos.quantity > 0:
                    price = current_prices.get(ts_code, 0)
                    order_id = self.place_order(ts_code, direction, price, pos.quantity)
                    if order_id > 0:
                        executed.append({'order_id': order_id, 'ts_code': ts_code, 'direction': direction})

        # 当日撮合
        trades = self.match_bar(current_prices, current_date)

        # 每日统计
        total_assets = self._account.total_assets(current_prices)
        prev_total = self._daily_stats[-1].total_assets if self._daily_stats else self._config.initial_capital
        daily_pnl = total_assets - prev_total
        daily_pnl_pct = daily_pnl / prev_total if prev_total > 0 else 0

        daily_trade_count = len(trades)
        daily_amount = sum(t.amount for t in trades)
        turnover = daily_amount / total_assets if total_assets > 0 else 0

        stats = DailyStats(
            date=current_date,
            total_assets=total_assets,
            cash=self._account.cash,
            market_value=self._account.market_value(current_prices),
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            turnover=turnover,
            trades=daily_trade_count,
        )
        self._daily_stats.append(stats)

        return {
            'success': True,
            'signals': signals,
            'executed_orders': executed,
            'filled_trades': trades,
            'daily_stats': stats,
        }

    def get_current_stats(self, current_prices: Dict[str, float]) -> DailyStats:
        """获取当前统计"""
        if not self._daily_stats:
            total_assets = self._account.total_assets(current_prices)
            return DailyStats(
                date=datetime.now(),
                total_assets=total_assets,
                cash=self._account.cash,
                market_value=self._account.market_value(current_prices),
                daily_pnl=0,
                daily_pnl_pct=0,
                turnover=0,
                trades=0,
            )
        return self._daily_stats[-1]

    def close_all(self, current_prices: Dict[str, float]) -> List[TradeRecord]:
        """平仓所有持仓"""
        closed_trades = []
        for ts_code, pos in self._account.get_all_positions().items():
            if pos.quantity > 0 and ts_code in current_prices:
                price = current_prices[ts_code]
                order_id = self.place_order(ts_code, TradeDirection.SELL, price, pos.quantity)
                if order_id > 0:
                    trade = self._fill_order(self._orders[order_id - 1], price)
                    if trade:
                        closed_trades.append(trade)
        return closed_trades

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'ok',
            'initial_capital': self._config.initial_capital,
            'current_cash': self._account.cash,
            'total_positions': self._account.count_positions(),
            'total_orders': len(self._orders),
            'total_trades': len(self._trades),
        }
