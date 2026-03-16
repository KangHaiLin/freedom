"""
策略研究子系统
- 策略管理：策略定义、版本管理
- 回测引擎：历史数据回测、性能评估
- 模拟交易：实盘模拟交易
- 策略验证：过拟合检测、参数敏感性分析
- 报告生成：回测结果可视化报告
"""
from .base import (
    BaseStrategy,
    BacktestResult,
    TradeRecord,
    StrategyStatus,
    TradeDirection,
    PositionSide,
    OrderType,
)
from .strategy_management import (
    StrategyManager,
    StrategyMetadata,
    StrategyVersion,
)
from .backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestPortfolio,
)
from .simulation_trading import (
    SimulationEngine,
    SimulationConfig,
    SimulationAccount,
)
from .strategy_validator import (
    detect_overfit,
    rolling_window_test,
    scan_parameter,
)
from .report_generator import (
    generate_text_report,
    generate_html_report,
    save_report,
)
from .strategy_manager import StrategyResearchManager

__version__ = "1.0.0"
__all__ = [
    # base
    'BaseStrategy',
    'BacktestResult',
    'TradeRecord',
    'StrategyStatus',
    'TradeDirection',
    'PositionSide',
    'OrderType',
    # strategy management
    'StrategyManager',
    'StrategyMetadata',
    'StrategyVersion',
    # backtest
    'BacktestEngine',
    'BacktestConfig',
    'BacktestPortfolio',
    # simulation
    'SimulationEngine',
    'SimulationConfig',
    'SimulationAccount',
    # validation
    'detect_overfit',
    'rolling_window_test',
    'scan_parameter',
    # report
    'generate_text_report',
    'generate_html_report',
    'save_report',
    # unified entry
    'StrategyResearchManager',
]
