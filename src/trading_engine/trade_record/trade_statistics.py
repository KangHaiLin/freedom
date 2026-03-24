"""
交易统计分析
计算胜率、盈亏比、最大回撤、收益曲线等统计指标
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.trading_engine.trade_record.trade_record import TradeRecord


class TradeStatistics:
    """交易统计分析计算器"""

    @staticmethod
    def calculate_basic_stats(trades: List[TradeRecord]) -> Dict[str, Any]:
        """
        计算基础统计指标
        Args:
            trades: 成交记录列表（一般只看卖出成交，因为只有卖出有实现盈亏）
        Returns:
            统计字典
        """
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "max_pnl": 0.0,
                "min_pnl": 0.0,
            }

        # 过滤有盈亏数据的交易
        pnl_trades = [t for t in trades if t.pnl is not None]
        if not pnl_trades:
            return {
                "total_trades": len(trades),
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "max_pnl": 0.0,
                "min_pnl": 0.0,
            }

        pnls = [t.pnl for t in pnl_trades]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p <= 0]

        total_pnl = sum(pnls)
        avg_pnl = total_pnl / len(pnls)

        return {
            "total_trades": len(pnl_trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(pnl_trades) if pnl_trades else 0.0,
            "total_pnl": total_pnl,
            "average_pnl": avg_pnl,
            "median_pnl": np.median(pnls) if pnls else 0.0,
            "std_pnl": np.std(pnls) if pnls else 0.0,
            "max_pnl": max(pnls) if pnls else 0.0,
            "min_pnl": min(pnls) if pnls else 0.0,
        }

    @staticmethod
    def calculate_profit_ratio(trades: List[TradeRecord]) -> Dict[str, float]:
        """
        计算盈亏比
        Args:
            trades: 成交记录列表
        Returns:
            盈亏比统计
        """
        if not trades:
            return {
                "profit_ratio": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "expectancy": 0.0,
            }

        pnl_trades = [t for t in trades if t.pnl is not None]
        if not pnl_trades:
            return {
                "profit_ratio": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "expectancy": 0.0,
            }

        winning = [t.pnl for t in pnl_trades if t.pnl > 0]
        losing = [abs(t.pnl) for t in pnl_trades if t.pnl < 0]

        avg_win = sum(winning) / len(winning) if winning else 0.0
        avg_loss = sum(losing) / len(losing) if losing else 0.0
        win_rate = len(winning) / len(pnl_trades) if pnl_trades else 0.0
        loss_rate = 1 - win_rate

        profit_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        # 期望值 = 胜率*平均赢 - 败率*平均输
        expectancy = win_rate * avg_win - loss_rate * avg_loss

        return {
            "profit_ratio": profit_ratio,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "win_rate": win_rate,
            "expectancy": expectancy,
        }

    @staticmethod
    def calculate_cumulative_pnl(trades: List[TradeRecord]) -> List[Dict[str, Any]]:
        """
        计算累计盈亏曲线
        Args:
            trades: 成交记录列表
        Returns:
            累计盈亏点列表，按时间排序
        """
        if not trades:
            return []

        # 按成交时间排序
        sorted_trades = sorted(trades, key=lambda t: t.filled_time)
        cumulative = []
        total = 0.0
        running_max = 0.0
        max_drawdown = 0.0

        for t in sorted_trades:
            if t.pnl is not None:
                total += t.pnl
            if total > running_max:
                running_max = total
            current_drawdown = running_max - total
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown

            cumulative.append(
                {
                    "trade_id": t.trade_id,
                    "ts_code": t.ts_code,
                    "filled_time": t.filled_time.isoformat(),
                    "pnl": t.pnl,
                    "cumulative_pnl": total,
                    "running_max": running_max,
                    "drawdown": current_drawdown,
                }
            )

        return cumulative

    @staticmethod
    def calculate_max_drawdown(cumulative: List[Dict[str, Any]]) -> float:
        """
        从累计盈亏计算最大回撤
        Args:
            cumulative: cumulative_pnl 输出
        Returns:
            最大回撤
        """
        if not cumulative:
            return 0.0
        return max(item["drawdown"] for item in cumulative)

    @staticmethod
    def calculate_by_strategy(trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """
        按策略分组统计
        Args:
            trades: 成交记录列表
        Returns:
            {strategy_id: 统计结果}
        """
        strategy_trades: Dict[str, List[TradeRecord]] = {}
        for trade in trades:
            sid = trade.strategy_id or "unknown"
            if sid not in strategy_trades:
                strategy_trades[sid] = []
            strategy_trades[sid].append(trade)

        result = {}
        for sid, st_trades in strategy_trades.items():
            basic = TradeStatistics.calculate_basic_stats(st_trades)
            ratio = TradeStatistics.calculate_profit_ratio(st_trades)
            result[sid] = {**basic, **ratio}

        return result

    @staticmethod
    def calculate_by_stock(trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """
        按股票分组统计
        Args:
            trades: 成交记录列表
        Returns:
            {ts_code: 统计结果}
        """
        stock_trades: Dict[str, List[TradeRecord]] = {}
        for trade in trades:
            if trade.ts_code not in stock_trades:
                stock_trades[trade.ts_code] = []
            stock_trades[trade.ts_code].append(trade)

        result = {}
        for ts_code, st_trades in stock_trades.items():
            basic = TradeStatistics.calculate_basic_stats(st_trades)
            ratio = TradeStatistics.calculate_profit_ratio(st_trades)
            result[ts_code] = {**basic, **ratio}

        return result

    @staticmethod
    def calculate_turnover_stats(trades: List[TradeRecord]) -> Dict[str, float]:
        """
        计算换手率和成交统计
        Args:
            trades: 成交记录列表
        Returns:
            统计结果
        """
        if not trades:
            return {
                "total_trades": 0,
                "total_turnover": 0.0,
                "total_commission": 0.0,
                "average_turnover_per_trade": 0.0,
                "average_commission_per_trade": 0.0,
            }

        total_turnover = sum(t.turnover for t in trades)
        total_commission = sum(t.commission for t in trades)
        n = len(trades)

        return {
            "total_trades": n,
            "total_turnover": total_turnover,
            "total_commission": total_commission,
            "average_turnover_per_trade": total_turnover / n,
            "average_commission_per_trade": total_commission / n,
            "commission_ratio": total_commission / total_turnover if total_turnover > 0 else 0.0,
        }

    @staticmethod
    def to_dataframe(trades: List[TradeRecord]) -> pd.DataFrame:
        """
        转换为DataFrame方便分析
        Args:
            trades: 成交记录列表
        Returns:
            DataFrame
        """
        data = []
        for t in trades:
            data.append(
                {
                    "trade_id": t.trade_id,
                    "order_id": t.order_id,
                    "ts_code": t.ts_code,
                    "side": t.side.name,
                    "filled_quantity": t.filled_quantity,
                    "filled_price": t.filled_price,
                    "filled_time": t.filled_time,
                    "strategy_id": t.strategy_id,
                    "commission": t.commission,
                    "slippage": t.slippage,
                    "pnl": t.pnl,
                    "turnover": t.turnover,
                    "net_turnover": t.net_turnover,
                }
            )
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values("filled_time")
        return df

    @staticmethod
    def generate_full_report(trades: List[TradeRecord]) -> Dict[str, Any]:
        """
        生成完整的统计报告
        Args:
            trades: 所有成交记录
        Returns:
            完整报告字典
        """
        # 只统计卖出交易（盈亏在这里计算）
        sell_trades = [t for t in trades if t.is_sell and t.pnl is not None]

        basic = TradeStatistics.calculate_basic_stats(sell_trades)
        profit_ratio = TradeStatistics.calculate_profit_ratio(sell_trades)
        cumulative = TradeStatistics.calculate_cumulative_pnl(trades)
        max_dd = TradeStatistics.calculate_max_drawdown(cumulative)
        turnover = TradeStatistics.calculate_turnover_stats(trades)
        by_strategy = TradeStatistics.calculate_by_strategy(trades)
        by_stock = TradeStatistics.calculate_by_stock(trades)

        return {
            "basic": basic,
            "profit_ratio": profit_ratio,
            "max_drawdown": max_dd,
            "turnover": turnover,
            "by_strategy": by_strategy,
            "by_stock": by_stock,
            "cumulative_pnl": cumulative,
            "total_trades_all": len(trades),
            "sell_trades_with_pnl": len(sell_trades),
        }
