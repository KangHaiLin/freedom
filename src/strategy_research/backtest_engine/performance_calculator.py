"""
绩效指标计算器
计算夏普比率、最大回撤、胜率等
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional

from src.strategy_research.base import DailyStats, BacktestResult, TradeRecord


def calculate_sharpe_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.03) -> float:
    """
    计算夏普比率

    Args:
        daily_returns: 日收益率序列
        risk_free_rate: 年化无风险利率

    Returns:
        夏普比率
    """
    if len(daily_returns) < 2:
        return 0.0

    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1
    excess_returns = daily_returns - daily_rf
    std = excess_returns.std()
    if std == 0:
        return 0.0

    return excess_returns.mean() / std * np.sqrt(252)


def calculate_max_drawdown(daily_cumulative: pd.Series) -> Tuple[float, Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """
    计算最大回撤

    Returns:
        (max_drawdown, peak_date, valley_date)
    """
    if len(daily_cumulative) < 2:
        return 0.0, None, None

    # 计算累计最大值
    running_max = daily_cumulative.cummax()
    # 计算回撤
    drawdown = (daily_cumulative - running_max) / running_max
    max_dd = drawdown.min()

    if abs(max_dd) < 1e-9:
        return 0.0, None, None

    # 找到最大回撤的起止点
    dd_idx = drawdown.idxmin()
    peak_idx = running_max.loc[:dd_idx].idxmax()

    return -max_dd, peak_idx, dd_idx


def calculate_metrics(
    daily_stats: List[DailyStats],
    trades: List[TradeRecord],
    initial_capital: float,
    final_capital: float,
) -> dict:
    """
    计算所有绩效指标

    Returns:
        指标字典
    """
    if not daily_stats:
        return {}

    # 构建日总资产序列
    dates = [ds.date for ds in daily_stats]
    total_assets = [ds.total_assets for ds in daily_stats]
    series = pd.Series(total_assets, index=dates)

    # 计算日收益率
    daily_returns = series.pct_change().dropna()

    # 年化收益率
    total_days = len(daily_returns)
    if total_days > 0:
        annualized_return = (final_capital / initial_capital) ** (252 / total_days) - 1
    else:
        annualized_return = 0.0

    # 夏普比率
    sharpe = calculate_sharpe_ratio(daily_returns)

    # 最大回撤
    max_dd, peak_date, valley_date = calculate_max_drawdown(series)

    # 交易统计
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl <= 0]
    total_trades = len(trades)
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

    # 盈亏比
    if len(losing_trades) > 0 and len(winning_trades) > 0:
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades)
        avg_loss = abs(sum(t.pnl for t in losing_trades) / len(losing_trades))
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    else:
        profit_loss_ratio = 0.0

    # 平均持有天数
    if total_trades > 0:
        # 简化：假设每笔交易平均持有天数近似为总天数除以交易次数的一半
        avg_holding_days = total_days / (total_trades / 2) if total_trades > 0 else 0
    else:
        avg_holding_days = 0

    # 年均换手率
    if total_days >= 252:
        turnover_annual = sum(ds.turnover for ds in daily_stats) * 252 / total_days
    else:
        turnover_annual = sum(ds.turnover for ds in daily_stats)

    return {
        'annualized_return': annualized_return * 100,  # 转为百分比
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd * 100,  # 转为百分比
        'max_drawdown_date_peak': peak_date,
        'max_drawdown_date_valley': valley_date,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate * 100,
        'profit_loss_ratio': profit_loss_ratio,
        'avg_holding_days': avg_holding_days,
        'turnover_rate_annual': turnover_annual * 100,
    }
