"""
策略研究基础模块
定义抽象基类和公共枚举
"""

from .base_strategy import BaseStrategy
from .enums import OrderType, PositionSide, StrategyStatus, TradeDirection
from .strategy_result import BacktestResult, DailyStats, PositionSnapshot, TradeRecord

__all__ = [
    "BaseStrategy",
    "BacktestResult",
    "TradeRecord",
    "PositionSnapshot",
    "DailyStats",
    "StrategyStatus",
    "TradeDirection",
    "PositionSide",
    "OrderType",
]
