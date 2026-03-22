"""
规则引擎模块
负责规则管理、规则执行、内置规则模板
"""

from .builtins import (
    create_daily_amount_limit_rule,
    create_delisted_block_rule,
    create_insufficient_cash_rule,
    create_insufficient_position_rule,
    create_limit_down_block_rule,
    create_limit_up_block_rule,
    create_max_positions_count_rule,
    create_single_position_concentration_rule,
    create_suspended_block_rule,
    get_default_pre_trade_rules,
)
from .rule import Rule, RuleVersion
from .rule_executor import RuleExecutor
from .rule_manager import RuleManager
from .rule_result import RuleResult, RuleViolation

__all__ = [
    # 核心类
    "Rule",
    "RuleVersion",
    "RuleResult",
    "RuleViolation",
    "RuleManager",
    "RuleExecutor",
    # 内置规则工厂方法
    "create_daily_amount_limit_rule",
    "create_single_position_concentration_rule",
    "create_max_positions_count_rule",
    "create_insufficient_cash_rule",
    "create_insufficient_position_rule",
    "create_limit_up_block_rule",
    "create_limit_down_block_rule",
    "create_suspended_block_rule",
    "create_delisted_block_rule",
    "get_default_pre_trade_rules",
]
