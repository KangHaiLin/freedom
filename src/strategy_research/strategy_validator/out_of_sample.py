"""
样本外测试
时间序列样本外测试
"""
from typing import Dict, List, Any, Tuple
import pandas as pd

from src.strategy_research.base import BaseStrategy, BacktestResult
from src.strategy_research.backtest_engine import BacktestEngine, BacktestConfig


def rolling_window_test(
    data: pd.DataFrame,
    strategy_class: type[BaseStrategy],
    params: Dict,
    train_window_days: int = 252 * 3,  # 3年训练
    test_window_days: int = 252,  # 1年测试
    config: BacktestConfig = None,
) -> Dict[str, Any]:
    """
    滚动窗口样本外测试

    Args:
        data: 完整数据集
        strategy_class: 策略类
        params: 策略参数
        train_window_days: 训练窗口天数
        test_window_days: 测试窗口天数
        config: 回测配置

    Returns:
        测试结果
    """
    dates = sorted(data['trade_date'].unique())
    total_days = len(dates)
    results: List[Dict] = []

    start = 0
    while start + train_window_days < total_days:
        train_end = start + train_window_days
        test_end = min(train_end + test_window_days, total_days)

        train_dates = dates[start:train_end]
        test_dates = dates[train_end:test_end]

        train_data = data[data['trade_date'].isin(train_dates)]
        test_data = data[data['trade_date'].isin(test_dates)]

        # 在训练集上跑一遍不需要，我们用固定参数
        # 这里主要是验证参数在样本外的表现
        train_engine = BacktestEngine(train_data, config)
        strategy_train = strategy_class(params=params)
        result_train = train_engine.run(strategy_train)

        test_engine = BacktestEngine(test_data, config)
        strategy_test = strategy_class(params=params)
        result_test = test_engine.run(strategy_test)

        results.append({
            'train_start': train_dates[0],
            'train_end': train_dates[-1],
            'test_start': test_dates[0],
            'test_end': test_dates[-1],
            'train_result': {
                'annualized_return': result_train.annualized_return,
                'sharpe_ratio': result_train.sharpe_ratio,
                'max_drawdown': result_train.max_drawdown,
            },
            'test_result': {
                'annualized_return': result_test.annualized_return,
                'sharpe_ratio': result_test.sharpe_ratio,
                'max_drawdown': result_test.max_drawdown,
                'total_trades': result_test.total_trades,
            },
        })

        start = train_end

    # 汇总
    if not results:
        return {'error': 'Not enough data'}

    train_returns = [r['train_result']['annualized_return'] for r in results]
    test_returns = [r['test_result']['annualized_return'] for r in results]

    avg_train_return = sum(train_returns) / len(train_returns) if train_returns else 0
    avg_test_return = sum(test_returns) / len(test_returns) if test_returns else 0
    return_decay = avg_train_return - avg_test_return

    train_sharpes = [r['train_result']['sharpe_ratio'] for r in results]
    test_sharpes = [r['test_result']['sharpe_ratio'] for r in results]

    avg_train_sharpe = sum(train_sharpes) / len(train_sharpes) if train_sharpes else 0
    avg_test_sharpe = sum(test_sharpes) / len(test_sharpes) if test_sharpes else 0
    sharpe_decay = avg_train_sharpe - avg_test_sharpe

    significant_decay = return_decay > 0.1 or sharpe_decay > 0.5

    return {
        'total_windows': len(results),
        'results': results,
        'average_train_return': avg_train_return * 100,
        'average_test_return': avg_test_return * 100,
        'return_decay': return_decay * 100,
        'average_train_sharpe': avg_train_sharpe,
        'average_test_sharpe': avg_test_sharpe,
        'sharpe_decay': sharpe_decay,
        'significant_decay': significant_decay,
        'overfit_suspected': significant_decay,
    }


def split_sample_test(
    data: pd.DataFrame,
    strategy_class: type[BaseStrategy],
    params: Dict,
    train_ratio: float = 0.7,
    config: BacktestConfig = None,
) -> Dict[str, Any]:
    """
    简单拆分样本内外测试

    Args:
        data: 完整数据集
        strategy_class: 策略类
        params: 策略参数
        train_ratio: 训练集比例
        config: 回测配置

    Returns:
        测试结果
    """
    dates = sorted(data['trade_date'].unique())
    split_idx = int(len(dates) * train_ratio)
    train_dates = dates[:split_idx]
    test_dates = dates[split_idx:]

    train_data = data[data['trade_date'].isin(train_dates)]
    test_data = data[data['trade_date'].isin(test_dates)]

    engine_train = BacktestEngine(train_data, config)
    strategy_train = strategy_class(params=params)
    result_train = engine_train.run(strategy_train)

    engine_test = BacktestEngine(test_data, config)
    strategy_test = strategy_class(params=params)
    result_test = engine_test.run(strategy_test)

    return_decay = result_train.annualized_return - result_test.annualized_return
    sharpe_decay = result_train.sharpe_ratio - result_test.sharpe_ratio
    significant_decay = return_decay > 0.1 or sharpe_decay > 0.5

    return {
        'train_size_days': len(train_dates),
        'test_size_days': len(test_dates),
        'train_result': {
            'annualized_return': result_train.annualized_return,
            'sharpe_ratio': result_train.sharpe_ratio,
            'max_drawdown': result_train.max_drawdown,
            'total_trades': result_train.total_trades,
        },
        'test_result': {
            'annualized_return': result_test.annualized_return,
            'sharpe_ratio': result_test.sharpe_ratio,
            'max_drawdown': result_test.max_drawdown,
            'total_trades': result_test.total_trades,
        },
        'return_decay': return_decay * 100,
        'sharpe_decay': sharpe_decay,
        'significant_decay': significant_decay,
        'overfit_suspected': significant_decay,
        'train_result_obj': result_train,
        'test_result_obj': result_test,
    }
