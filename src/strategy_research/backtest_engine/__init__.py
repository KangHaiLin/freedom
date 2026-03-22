"""
回测引擎
- 配置回测参数
- 驱动策略逐K线执行
- 撮合交易计算
- 绩效指标计算
"""

from .backtest_config import BacktestConfig
from .backtest_engine import BacktestEngine
from .backtest_portfolio import BacktestPortfolio, Position
from .performance_calculator import calculate_max_drawdown, calculate_metrics, calculate_sharpe_ratio

__all__ = [
    "BacktestConfig",
    "BacktestPortfolio",
    "Position",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_metrics",
    "BacktestEngine",
]
