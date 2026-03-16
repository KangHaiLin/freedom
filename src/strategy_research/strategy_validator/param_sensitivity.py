"""
参数敏感性分析
测试不同参数对策略表现的影响
"""
from typing import Dict, List, Any, Callable, Tuple
import pandas as pd
import numpy as np

from src.strategy_research.base import BaseStrategy, BacktestResult
from src.strategy_research.backtest_engine import BacktestEngine, BacktestConfig


def scan_parameter(
    parameter_name: str,
    values: List[Any],
    base_params: Dict,
    strategy_class: Callable[..., BaseStrategy],
    backtest_engine: BacktestEngine,
) -> Dict[str, Any]:
    """
    参数扫描

    Args:
        parameter_name: 参数名称
        values: 要测试的参数值列表
        base_params: 基础参数
        strategy_class: 策略类
        backtest_engine: 回测引擎

    Returns:
        扫描结果
    """
    results: List[Dict] = []

    for value in values:
        params = base_params.copy()
        params[parameter_name] = value

        strategy = strategy_class(params=params)
        result = backtest_engine.run(strategy)

        results.append({
            'parameter_value': value,
            'annualized_return': result.annualized_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'total_trades': result.total_trades,
            'result': result,
        })

    # 分析稳定性
    returns = [r['annualized_return'] for r in results]
    sharpe = [r['sharpe_ratio'] for r in results]
    return_std = np.std(returns)
    sharpe_std = np.std(sharpe)

    # 高波动说明敏感性高
    high_sensitivity = return_std > 0.1  # 标准差超过10%

    return {
        'parameter_name': parameter_name,
        'values': values,
        'results': results,
        'return_std': return_std,
        'sharpe_std': sharpe_std,
        'high_sensitivity': high_sensitivity,
        'best_value': values[np.argmax(returns)],
        'best_return': max(returns),
        'best_sharpe': max(sharpe),
    }


def grid_search(
    param_grid: Dict[str, List[Any]],
    base_params: Dict,
    strategy_class: Callable[..., BaseStrategy],
    backtest_engine: BacktestEngine,
    optimize_metric: str = 'sharpe_ratio',
) -> Dict[str, Any]:
    """
    网格搜索

    Args:
        param_grid: 参数网格 {param_name: [values]}
        base_params: 基础参数
        strategy_class: 策略类
        backtest_engine: 回测引擎
        optimize_metric: 优化目标指标

    Returns:
        网格搜索结果
    """
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    results: List[Dict] = []

    # 递归生成所有组合
    def generate_combinations(index: int, current: Dict) -> None:
        if index == len(param_names):
            combined = base_params.copy()
            combined.update(current)
            strategy = strategy_class(params=combined)
            result = backtest_engine.run(strategy)

            result_dict = combined.copy()
            result_dict['annualized_return'] = result.annualized_return
            result_dict['sharpe_ratio'] = result.sharpe_ratio
            result_dict['max_drawdown'] = result.max_drawdown
            result_dict['total_trades'] = result.total_trades
            result_dict['result'] = result
            results.append(result_dict)
            return

        param_name = param_names[index]
        for value in param_values[index]:
            current[param_name] = value
            generate_combinations(index + 1, current)

    generate_combinations(0, {})

    # 找到最优参数
    if optimize_metric == 'sharpe_ratio':
        best = max(results, key=lambda x: x['sharpe_ratio'])
    elif optimize_metric == 'annualized_return':
        best = max(results, key=lambda x: x['annualized_return'])
    else:
        best = min(results, key=lambda x: x['max_drawdown'])

    return {
        'all_results': results,
        'best_parameters': {k: best[k] for k in param_names},
        'best_result': best,
        'optimize_metric': optimize_metric,
    }


def sensitivity_summary(sensitivity_results: List[Dict]) -> Dict[str, Any]:
    """
    汇总多个参数敏感性结果

    Returns:
        总结：哪些参数敏感性高
    """
    high_sensitivity_params = [r['parameter_name'] for r in sensitivity_results if r['high_sensitivity']]
    low_sensitivity_params = [r['parameter_name'] for r in sensitivity_results if not r['high_sensitivity']]

    return {
        'high_sensitivity_params': high_sensitivity_params,
        'low_sensitivity_params': low_sensitivity_params,
        'total_parameters': len(sensitivity_results),
        'high_sensitivity_count': len(high_sensitivity_params),
    }
