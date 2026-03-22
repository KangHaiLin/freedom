"""
内置规则模板
预定义常见风控规则
"""

from typing import Any, Dict, Optional

from src.risk_management.base.base_rule import RuleLevel, RuleType
from src.risk_management.rule_engine.rule import Rule

# ========== 预定义交易前检查规则 ==========


def create_daily_amount_limit_rule(
    limit_amount: float,
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    创建单日累计交易额限额规则

    Args:
        limit_amount: 单日累计限额
        level: 规则级别

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        """检查: 当前买入后是否超过限额"""
        current_daily = ctx.get("current_daily_buy_amount", 0.0)
        order_amount = ctx.get("price", 0.0) * ctx.get("quantity", 0)
        return (current_daily + order_amount) <= limit_amount

    def message(ctx: Dict[str, Any]) -> str:
        current = ctx.get("current_daily_buy_amount", 0.0)
        order_amount = ctx.get("price", 0.0) * ctx.get("quantity", 0)
        return f"单日累计买入金额已超过限额: 当前{current+order_amount:.2f}, 限额{limit_amount:.2f}"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        current = ctx.get("current_daily_buy_amount", 0.0)
        order_amount = ctx.get("price", 0.0) * ctx.get("quantity", 0)
        return {
            "current_amount": current + order_amount,
            "limit_amount": limit_amount,
        }

    return Rule(
        rule_id="RULE-PRE-001",
        rule_name="单日累计交易额限额",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description=f"限制用户单日累计买入金额不超过{limit_amount:.2f}",
    )


def create_single_position_concentration_rule(
    max_ratio: float = 0.3,
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    创建单票持仓集中度限制规则

    Args:
        max_ratio: 最大持仓比例（占总资产），默认30%
        level: 规则级别

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        total_asset = ctx.get("total_asset", 0.0)
        if total_asset <= 0:
            return True
        current_quantity = ctx.get("current_quantity", 0)
        price = ctx.get("price", 0.0)
        order_quantity = ctx.get("quantity", 0)
        total_value = (current_quantity + order_quantity) * price
        ratio = total_value / total_asset
        return ratio <= max_ratio

    def message(ctx: Dict[str, Any]) -> str:
        total_asset = ctx.get("total_asset", 0.0)
        current_quantity = ctx.get("current_quantity", 0)
        price = ctx.get("price", 0.0)
        order_quantity = ctx.get("quantity", 0)
        total_value = (current_quantity + order_quantity) * price
        ratio = total_value / total_asset if total_asset > 0 else 0
        return f"单票持仓比例超限: 当前{ratio*100:.1f}%, 限制{max_ratio*100:.1f}%"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        total_asset = ctx.get("total_asset", 0.0)
        current_quantity = ctx.get("current_quantity", 0)
        price = ctx.get("price", 0.0)
        order_quantity = ctx.get("quantity", 0)
        total_value = (current_quantity + order_quantity) * price
        ratio = total_value / total_asset if total_asset > 0 else 0
        return {
            "current_ratio": ratio,
            "max_ratio": max_ratio,
            "current_value": total_value,
            "total_asset": total_asset,
        }

    return Rule(
        rule_id="RULE-PRE-002",
        rule_name="单票持仓集中度限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description=f"单只股票持仓比例不得超过总资产的{max_ratio*100:.0f}%",
    )


def create_max_positions_count_rule(
    max_count: int = 20,
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    创建最大持仓数量限制规则

    Args:
        max_count: 最大持仓股票数量
        level: 规则级别

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        current_count = ctx.get("current_position_count", 0)
        ts_code = ctx.get("ts_code", "")
        has_position = ctx.get("has_existing_position", False)
        if not has_position:
            return (current_count + 1) <= max_count
        return current_count <= max_count

    def message(ctx: Dict[str, Any]) -> str:
        current_count = ctx.get("current_position_count", 0)
        ts_code = ctx.get("ts_code", "")
        has_position = ctx.get("has_existing_position", False)
        new_count = current_count if has_position else current_count + 1
        return f"持仓股票数量超出限制: 当前{new_count}, 最大{max_count}"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        current_count = ctx.get("current_position_count", 0)
        has_position = ctx.get("has_existing_position", False)
        return {
            "current_count": current_count,
            "new_count": current_count if has_position else current_count + 1,
            "max_count": max_count,
        }

    return Rule(
        rule_id="RULE-PRE-003",
        rule_name="最大持仓数量限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description=f"限制最大持仓股票数量不超过{max_count}只",
    )


def create_insufficient_cash_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    创建可用资金不足检查规则

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        available_cash = ctx.get("available_cash", 0.0)
        required_amount = ctx.get("required_amount", 0.0)
        return available_cash >= required_amount

    def message(_: Dict[str, Any]) -> str:
        return "可用资金不足，无法买入"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "available_cash": ctx.get("available_cash", 0.0),
            "required_amount": ctx.get("required_amount", 0.0),
        }

    return Rule(
        rule_id="RULE-PRE-004",
        rule_name="可用资金不足检查",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="买入前检查可用资金是否足够",
    )


def create_insufficient_position_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    创建持仓不足卖出检查规则

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        side = ctx.get("side", "").upper()
        # Only check for SELL, BUY always passes
        if side != "SELL":
            return True
        available_quantity = ctx.get("available_quantity", 0)
        sell_quantity = ctx.get("quantity", 0)
        return available_quantity >= sell_quantity

    def message(_: Dict[str, Any]) -> str:
        return "可用持仓不足，无法卖出"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "available_quantity": ctx.get("available_quantity", 0),
            "sell_quantity": ctx.get("quantity", 0),
        }

    return Rule(
        rule_id="RULE-PRE-005",
        rule_name="持仓不足卖出检查",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="卖出前检查可用持仓是否足够，含T+1限制",
    )


def create_limit_up_block_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    涨停买入限制规则
    一般风控策略会禁止追涨停，可配置开启

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        is_limit_up = ctx.get("is_limit_up", False)
        # 如果是涨停且是买入，禁止
        side = ctx.get("side", "")
        if is_limit_up and side == "BUY":
            return False
        return True

    def message(_: Dict[str, Any]) -> str:
        return "股票已涨停，禁止买入"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ts_code": ctx.get("ts_code", ""),
            "is_limit_up": True,
        }

    return Rule(
        rule_id="RULE-PRE-006",
        rule_name="涨停买入限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="禁止买入涨停板股票",
    )


def create_limit_down_block_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    跌停卖出限制规则

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        is_limit_down = ctx.get("is_limit_down", False)
        side = ctx.get("side", "")
        if is_limit_down and side == "SELL":
            return False
        return True

    def message(_: Dict[str, Any]) -> str:
        return "股票已跌停，无法卖出"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ts_code": ctx.get("ts_code", ""),
            "is_limit_down": True,
        }

    return Rule(
        rule_id="RULE-PRE-007",
        rule_name="跌停卖出限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="禁止卖出跌停板股票",
    )


def create_suspended_block_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    停牌禁止交易规则

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        return not ctx.get("is_suspended", False)

    def message(_: Dict[str, Any]) -> str:
        return "股票处于停牌状态，禁止交易"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ts_code": ctx.get("ts_code", ""),
            "is_suspended": True,
        }

    return Rule(
        rule_id="RULE-PRE-008",
        rule_name="停牌交易限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="停牌股票禁止交易",
    )


def create_delisted_block_rule(
    level: RuleLevel = RuleLevel.BLOCK,
) -> Rule:
    """
    退市股票禁止交易规则

    Returns:
        规则对象
    """

    def check(ctx: Dict[str, Any]) -> bool:
        return not ctx.get("is_delisted", False)

    def message(_: Dict[str, Any]) -> str:
        return "股票已退市，禁止交易"

    def details(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ts_code": ctx.get("ts_code", ""),
            "is_delisted": True,
        }

    return Rule(
        rule_id="RULE-PRE-009",
        rule_name="退市交易限制",
        rule_group="pre_trade",
        check_func=check,
        message_func=message,
        details_func=details,
        level=level,
        description="退市股票禁止交易",
    )


def get_default_pre_trade_rules() -> list:
    """获取默认预定义的交易前检查规则集合"""
    return [
        create_delisted_block_rule(),
        create_suspended_block_rule(),
        create_limit_up_block_rule(RuleLevel.WARNING),
        create_limit_down_block_rule(),
        create_insufficient_cash_rule(),
        create_insufficient_position_rule(),
        create_single_position_concentration_rule(),
        create_max_positions_count_rule(),
    ]
