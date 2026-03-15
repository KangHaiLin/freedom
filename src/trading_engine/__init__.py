"""
交易系统子系统 (Trading Engine)
负责订单管理、持仓管理、执行引擎、券商接口、风险控制等核心交易功能

模块结构:
- base/ - 基础抽象类定义
- order_management/ - 订单管理
- position_management/ - 持仓管理
- trade_record/ - 交易记录
- broker_adapter/ - 券商适配器
- execution_engine/ - 执行引擎（算法交易）
- risk_control/ - 风险控制
- trading_manager.py - 统一交易管理器入口
"""
from .base import (
    BaseOrder,
    BasePosition,
    BaseBrokerAdapter,
    OrderSide,
    OrderType,
    OrderStatus,
)

__version__ = "0.1.0"

__all__ = [
    # 基础抽象类
    'BaseOrder',
    'BasePosition',
    'BaseBrokerAdapter',
    # 枚举
    'OrderSide',
    'OrderType',
    'OrderStatus',
]
