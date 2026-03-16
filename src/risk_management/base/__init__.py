"""
风险管理子系统 - 基础抽象层
定义规则、违规结果的抽象基类
"""
from .base_rule import BaseRule, RuleLevel, RuleType
from .base_violation import BaseViolation, ViolationLevel

__all__ = [
    # 规则抽象基类
    'BaseRule',
    # 枚举
    'RuleLevel',
    'RuleType',
    # 违规结果抽象基类
    'BaseViolation',
    'ViolationLevel',
]
