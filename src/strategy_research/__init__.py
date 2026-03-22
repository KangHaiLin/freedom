"""
策略研究子系统
- 策略管理：策略定义、版本管理
- 回测引擎：历史数据回测、性能评估
- 模拟交易：实盘模拟交易
- 策略验证：过拟合检测、参数敏感性分析
- 报告生成：回测结果可视化报告
"""

from .backtest_engine import BacktestConfig, BacktestEngine, BacktestPortfolio
from .base import BacktestResult, BaseStrategy, OrderType, PositionSide, StrategyStatus, TradeDirection, TradeRecord
from .report_generator import generate_html_report, generate_text_report, save_report
from .simulation_trading import SimulationAccount, SimulationConfig, SimulationEngine
from .strategy_management import StrategyManager, StrategyMetadata, StrategyVersion
from .strategy_manager import StrategyResearchManager
from .strategy_validator import detect_overfit, rolling_window_test, scan_parameter

__version__ = "1.0.0"
__all__ = [
    # base
    "BaseStrategy",
    "BacktestResult",
    "TradeRecord",
    "StrategyStatus",
    "TradeDirection",
    "PositionSide",
    "OrderType",
    # strategy management
    "StrategyManager",
    "StrategyMetadata",
    "StrategyVersion",
    # backtest
    "BacktestEngine",
    "BacktestConfig",
    "BacktestPortfolio",
    # simulation
    "SimulationEngine",
    "SimulationConfig",
    "SimulationAccount",
    # validation
    "detect_overfit",
    "rolling_window_test",
    "scan_parameter",
    # report
    "generate_text_report",
    "generate_html_report",
    "save_report",
    # unified entry
    "StrategyResearchManager",
]
