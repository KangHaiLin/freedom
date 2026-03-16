"""
规则执行器
执行规则匹配和检查，返回检查结果
"""
from typing import Dict, Any, List, Optional
import logging
from src.risk_management.base.base_rule import BaseRule, RuleLevel
from src.risk_management.base.base_violation import ViolationLevel
from .rule_manager import RuleManager
from .rule_result import RuleResult, RuleViolation

logger = logging.getLogger(__name__)


class RuleExecutor:
    """
    规则执行器
    执行业务上下文的规则检查，返回检查结果
    """

    def __init__(self, rule_manager: RuleManager):
        self._rule_manager = rule_manager

    def execute(
        self,
        rule_group: str,
        context: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> RuleResult:
        """
        执行指定规则组的所有规则检查

        Args:
            rule_group: 规则组名称
            context: 检查上下文（订单、持仓等信息）
            user_id: 用户ID，用于灰度规则判断

        Returns:
            规则执行结果
        """
        result = RuleResult()
        rules = self._rule_manager.get_rules_by_group(rule_group)
        result.set_fired_rules(len(rules))

        for rule in rules:
            try:
                # 执行规则检查
                if not rule.check(context):
                    # 违规，添加到结果
                    level_map = {
                        RuleLevel.INFO: ViolationLevel.INFO,
                        RuleLevel.WARNING: ViolationLevel.WARNING,
                        RuleLevel.ERROR: ViolationLevel.ERROR,
                        RuleLevel.BLOCK: ViolationLevel.CRITICAL,
                    }
                    violation = RuleViolation(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        level=level_map.get(rule.level, ViolationLevel.WARNING),
                        message=rule.get_violation_message(context),
                        details=rule.get_violation_details(context),
                    )
                    result.add_violation(violation)

                    # 如果遇到阻断级别的违规，可以提前退出不检查后续规则
                    if violation.is_blocking():
                        logger.debug(
                            f"Blocked by rule {rule.rule_id}: {violation.message}"
                        )
                        break

            except Exception as e:
                logger.error(f"Error executing rule {rule.rule_id}: {e}")
                # 规则执行异常时，根据配置决定处理策略
                # 默认：继续执行其他规则，不阻断
                continue

        return result

    def execute_single(
        self,
        rule_id: str,
        context: Dict[str, Any],
    ) -> Optional[RuleResult]:
        """
        执行单个规则检查

        Args:
            rule_id: 规则ID
            context: 检查上下文

        Returns:
            执行结果，如果规则不存在返回None
        """
        rule = self._rule_manager.get_rule(rule_id)
        if rule is None:
            return None

        result = RuleResult()
        result.set_fired_rules(1)

        try:
            if not rule.check(context):
                level_map = {
                    RuleLevel.INFO: ViolationLevel.INFO,
                    RuleLevel.WARNING: ViolationLevel.WARNING,
                    RuleLevel.ERROR: ViolationLevel.ERROR,
                    RuleLevel.BLOCK: ViolationLevel.CRITICAL,
                }
                violation = RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    level=level_map.get(rule.level, ViolationLevel.WARNING),
                    message=rule.get_violation_message(context),
                    details=rule.get_violation_details(context),
                )
                result.add_violation(violation)
        except Exception as e:
            logger.error(f"Error executing single rule {rule_id}: {e}")

        return result

    def execute_batch(
        self,
        rule_group: str,
        contexts: List[Dict[str, Any]],
    ) -> List[RuleResult]:
        """
        批量执行规则检查

        Args:
            rule_group: 规则组
            contexts: 上下文列表

        Returns:
            执行结果列表，与输入顺序对应
        """
        return [self.execute(rule_group, ctx) for ctx in contexts]

    def get_all_enabled_rules(self) -> List[BaseRule]:
        """获取所有启用的规则"""
        return [r for r in self._rule_manager.get_all_rules() if r.is_enabled()]
