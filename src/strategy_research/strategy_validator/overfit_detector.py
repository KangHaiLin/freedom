"""
过拟合检测器
检测策略是否过拟合
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.strategy_research.base import BacktestResult


def calculate_information_ratio(returns: pd.Series, target_vol: float = 0.15) -> float:
    """计算信息比率"""
    if len(returns) < 2:
        return 0.0
    mean = returns.mean()
    std = returns.std()
    if std == 0:
        return 0.0
    return mean / std


def calculate_drawdown_calmar(returns: pd.Series) -> float:
    """计算Calmar比率"""
    if len(returns) < 2:
        return 0.0

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = -drawdown.min()

    if max_dd == 0:
        return 0.0

    annual_return = (cumulative.iloc[-1]) ** (252 / len(returns)) - 1
    return annual_return / max_dd


def detect_overfit(
    backtest_result: BacktestResult,
    threshold_sharpe: float = 2.0,
    threshold_drawdown_ratio: float = 0.5,
) -> Dict[str, Any]:
    """
    检测过拟合

    Args:
        backtest_result: 回测结果
        threshold_sharpe: 过高夏普比率阈值，超过怀疑过拟合
        threshold_drawdown_ratio: 最大回撤/收益阈值，过低怀疑过拟合

    Returns:
        检测结果
    """
    # 提取日收益率
    daily_returns = []
    for i in range(1, len(backtest_result.daily_stats)):
        prev = backtest_result.daily_stats[i - 1].total_assets
        curr = backtest_result.daily_stats[i].total_assets
        ret = (curr - prev) / prev if prev > 0 else 0
        daily_returns.append(ret)

    if not daily_returns:
        return {
            "is_overfit": False,
            "message": "Insufficient data",
            "sharpe_ratio": 0,
            "calmar_ratio": 0,
        }

    returns_series = pd.Series(daily_returns)
    sharpe = backtest_result.sharpe_ratio
    calmar = backtest_result.annualized_return / backtest_result.max_drawdown if backtest_result.max_drawdown > 0 else 0

    is_overfit = False
    warnings = []

    # 夏普比率异常高怀疑过拟合
    if sharpe > threshold_sharpe:
        is_overfit = True
        warnings.append(f"High Sharpe ratio {sharpe:.2f} exceeds threshold {threshold_sharpe}, possible overfitting")

    # 收益高但回撤更大，可能过拟合
    if (
        backtest_result.max_drawdown > 0
        and backtest_result.annualized_return / backtest_result.max_drawdown < threshold_drawdown_ratio
    ):
        is_overfit = True
        warnings.append(
            f"Low return/drawdown ratio {(backtest_result.annualized_return / backtest_result.max_drawdown):.2f}, possible overfitting"
        )

    # 交易太少怀疑过度拟合
    if backtest_result.total_trades < 10:
        warnings.append(
            f"Very few trades ({backtest_result.total_trades}), possible overfitting or too restrictive strategy"
        )

    return {
        "is_overfit": is_overfit,
        "warnings": warnings,
        "sharpe_ratio": sharpe,
        "calmar_ratio": calmar,
        "total_trades": backtest_result.total_trades,
        "annualized_return": backtest_result.annualized_return,
        "max_drawdown": backtest_result.max_drawdown,
    }


def walk_forward_analysis(
    backtest_results: List[BacktestResult],
) -> Dict[str, Any]:
    """
    滚窗口分析
    评估样本外表现检测过拟合

    Args:
        backtest_results: 多个窗口的回测结果列表[训练集, 测试集, ...]

    Returns:
        分析结果
    """
    in_sample_returns = []
    out_sample_returns = []

    for i in range(0, len(backtest_results), 2):
        if i + 1 >= len(backtest_results):
            break
        in_sample = backtest_results[i]
        out_sample = backtest_results[i + 1]
        in_sample_returns.append(in_sample.annualized_return)
        out_sample_returns.append(out_sample.annualized_return)

    if not in_sample_returns or not out_sample_returns:
        return {"error": "No paired results"}

    avg_in = np.mean(in_sample_returns)
    avg_out = np.mean(out_sample_returns)

    # 衰减 = 样本内 - 样本外
    decay = avg_in - avg_out
    is_significant_decay = decay > 0.1  # 衰减超过10%年化

    return {
        "average_in_sample_return": avg_in * 100,
        "average_out_sample_return": avg_out * 100,
        "return_decay": decay * 100,
        "significant_decay": is_significant_decay,
        "overfit_suspected": is_significant_decay,
    }
