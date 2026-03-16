"""
策略研究基础模块
定义抽象基类和公共枚举
"""
from .base_strategy import BaseStrategy
from .strategy_result import BacktestResult, TradeRecord, PositionSnapshot, DailyStats
from .enums import (
    StrategyStatus,
    TradeDirection,
    PositionSide,
    OrderType,
)

__all__ = [
    'BaseStrategy',
    'BacktestResult',
    'TradeRecord',
    'PositionSnapshot',
    'DailyStats',
    'StrategyStatus',
    'TradeDirection',
    'PositionSide',
    'OrderType',
]
