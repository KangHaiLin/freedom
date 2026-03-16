"""
风险管理子系统 (Risk Management)
负责全系统的风险监控、合规检查、风险预警和风险控制，保障交易系统的安全性和合规性。

模块结构:
- base/ - 基础抽象类定义
- rule_engine/ - 规则引擎核心模块
- realtime_monitor/ - 实时风险监控模块
- compliance_management/ - 合规管理模块
- risk_calculation/ - 风险计算和限额管理模块
- audit_trail/ - 审计跟踪模块
- risk_manager.py - 统一风险管理管理器入口
"""
from .base import (
    BaseRule,
    BaseViolation,
    RuleLevel,
    RuleType,
    ViolationLevel,
)
from .risk_manager import RiskManager

__version__ = "0.1.0"

__all__ = [
    # 基础抽象类
    'BaseRule',
    'BaseViolation',
    # 枚举
    'RuleLevel',
    'RuleType',
    'ViolationLevel',
    # 统一入口
    'RiskManager',
]
