"""
交易记录模块
- TradeRecord: 单次成交记录
- TradeRecordManager: 成交记录管理器，管理所有成交记录
- TradeStatistics: 交易统计分析，计算胜率、盈亏比、最大回撤等
"""

from .trade_record import TradeRecord
from .trade_record_manager import TradeRecordManager
from .trade_statistics import TradeStatistics

__all__ = [
    "TradeRecord",
    "TradeRecordManager",
    "TradeStatistics",
]
