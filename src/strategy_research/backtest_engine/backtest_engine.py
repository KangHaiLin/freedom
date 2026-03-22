"""
回测引擎核心
驱动回测执行，调用策略，撮合交易，计算结果
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.strategy_research.base import (
    BacktestResult,
    BaseStrategy,
    DailyStats,
    PositionSnapshot,
    TradeDirection,
    TradeRecord,
)

from .backtest_config import BacktestConfig
from .backtest_portfolio import BacktestPortfolio
from .performance_calculator import calculate_metrics


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        data: pd.DataFrame,
        config: Optional[BacktestConfig] = None,
    ):
        """
        初始化回测引擎

        Args:
            data: 复权K线数据，需要包含 columns: [trade_date, ts_code, open, high, low, close, vol]
            data 应该是按日期分组的面板数据
            config: 回测配置
        """
        self._data = data.copy()
        self._data.sort_values(["trade_date", "ts_code"], inplace=True)
        self._config = config or BacktestConfig()
        self._portfolio = BacktestPortfolio(self._config)

        # 按日期分组
        self._dates = sorted(self._data["trade_date"].unique())
        self._date_data = {d: self._data[self._data["trade_date"] == d] for d in self._dates}

    def run(self, strategy: BaseStrategy) -> BacktestResult:
        """
        执行回测

        Args:
            strategy: 策略实例

        Returns:
            回测结果
        """
        # 初始化策略
        strategy.initialize()

        trade_id_counter = 1
        all_trades: List[TradeRecord] = []
        all_daily_stats: List[DailyStats] = []
        all_position_snapshots: List[Dict[str, PositionSnapshot]] = []

        # 过滤日期范围
        filtered_dates = self._dates
        if self._config.start_date is not None:
            filtered_dates = [d for d in filtered_dates if d >= self._config.start_date]
        if self._config.end_date is not None:
            filtered_dates = [d for d in filtered_dates if d <= self._config.end_date]

        for current_date in filtered_dates:
            bar_data = self._date_data[current_date]

            # 获取当前收盘价
            current_prices: Dict[str, float] = {}
            for _, row in bar_data.iterrows():
                current_prices[row["ts_code"]] = row["close"]

            # 获取当前信号
            signals = strategy.on_bar(bar_data, current_date, self._portfolio)

            # 执行信号
            for ts_code, direction in signals.items():
                if direction == TradeDirection.BUY:
                    # 计算可买数量（整手，100股整数倍）
                    price = current_prices[ts_code]
                    max_quantity = int(self._portfolio.cash // (price * 100)) * 100
                    if max_quantity <= 0:
                        continue

                    # 检查最大持仓比例限制
                    if self._config.single_position_max_ratio is not None:
                        total_assets = self._portfolio.total_assets(current_prices)
                        max_value = total_assets * self._config.single_position_max_ratio
                        max_quantity_new = int(max_value // (price * 100)) * 100
                        current_pos = self._portfolio.get_position(ts_code).quantity
                        max_quantity = min(max_quantity, max_quantity_new - current_pos)

                    if max_quantity > 0:
                        trade = self._portfolio.buy(ts_code, price, max_quantity)
                        trade.trade_id = trade_id_counter
                        trade.trade_date = current_date
                        all_trades.append(trade)
                        strategy.on_trade(trade, self._portfolio)
                        trade_id_counter += 1

                elif direction == TradeDirection.SELL:
                    pos = self._portfolio.get_position(ts_code)
                    if pos.quantity > 0:
                        price = current_prices[ts_code]
                        trade = self._portfolio.sell(ts_code, price, pos.quantity)
                        trade.trade_id = trade_id_counter
                        trade.trade_date = current_date
                        all_trades.append(trade)
                        strategy.on_trade(trade, self._portfolio)
                        trade_id_counter += 1

            # 检查最大持仓数量限制
            if self._config.max_position_count is not None:
                # 如果超过限制，不再接受新买入，但是我们已经买入了，这里只是检查，不强制平仓
                pass

            # 每日统计
            total_assets = self._portfolio.total_assets(current_prices)
            prev_total = all_daily_stats[-1].total_assets if all_daily_stats else self._config.initial_capital
            daily_pnl = total_assets - prev_total
            daily_pnl_pct = daily_pnl / prev_total if prev_total > 0 else 0

            # 计算换手率 = 今日交易金额 / 总资产
            daily_trade_amount = sum(t.amount for t in all_trades if t.trade_date == current_date)
            turnover = daily_trade_amount / total_assets if total_assets > 0 else 0

            daily_stats = DailyStats(
                date=current_date,
                total_assets=total_assets,
                cash=self._portfolio.cash,
                market_value=self._portfolio.market_value(current_prices),
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                turnover=turnover,
                trades=sum(1 for t in all_trades if t.trade_date == current_date),
            )
            all_daily_stats.append(daily_stats)

            # 持仓快照
            snapshot = self._portfolio.get_snapshot(current_prices)
            all_position_snapshots.append(snapshot)

        # 回测结束平仓
        if self._config.close_at_end:
            last_date = filtered_dates[-1]
            last_prices: Dict[str, float] = {}
            for _, row in self._date_data[last_date].iterrows():
                last_prices[row["ts_code"]] = row["close"]
            close_trades = self._portfolio.close_all(last_prices)
            for trade in close_trades:
                trade.trade_id = trade_id_counter
                trade.trade_date = last_date
                all_trades.append(trade)
                trade_id_counter += 1

            # 更新最后一天统计
            total_assets = self._portfolio.total_assets(last_prices)
            prev_total = all_daily_stats[-1].total_assets
            daily_pnl = total_assets - prev_total
            daily_pnl_pct = daily_pnl / prev_total if prev_total > 0 else 0
            all_daily_stats[-1].total_assets = total_assets
            all_daily_stats[-1].daily_pnl = daily_pnl
            all_daily_stats[-1].daily_pnl_pct = daily_pnl_pct
            all_daily_stats[-1].market_value = self._portfolio.market_value(last_prices)
            snapshot = self._portfolio.get_snapshot(last_prices)
            all_position_snapshots[-1] = snapshot

        # 计算最终结果
        initial_cap = self._config.initial_capital
        final_cap = self._portfolio.total_assets(
            {ts: pos.current_price for ts, pos in all_position_snapshots[-1].items()}
        )
        total_pnl = final_cap - initial_cap
        total_pnl_pct = total_pnl / initial_cap

        # 计算绩效指标
        metrics = calculate_metrics(all_daily_stats, all_trades, initial_cap, final_cap)

        # 回测结束回调
        extra_info = strategy.on_backtest_end(self._portfolio, all_trades)

        result = BacktestResult(
            strategy_name=strategy.name,
            initial_capital=initial_cap,
            final_capital=final_cap,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct * 100,
            annualized_return=metrics.get("annualized_return", 0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            max_drawdown_date=metrics.get("max_drawdown_date_valley", None),
            win_rate=metrics.get("win_rate", 0),
            profit_loss_ratio=metrics.get("profit_loss_ratio", 0),
            total_trades=metrics.get("total_trades", 0),
            winning_trades=metrics.get("winning_trades", 0),
            losing_trades=metrics.get("losing_trades", 0),
            avg_holding_days=metrics.get("avg_holding_days", 0),
            turnover_rate=metrics.get("turnover_rate_annual", 0),
            daily_stats=all_daily_stats,
            trades=all_trades,
            positions=all_position_snapshots,
            extra_info=extra_info,
        )

        return result

    def get_portfolio(self) -> BacktestPortfolio:
        """获取当前投资组合"""
        return self._portfolio
