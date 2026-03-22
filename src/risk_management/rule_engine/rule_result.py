"""
规则执行结果封装类
封装一次规则检查的结果
"""

from typing import Any, Dict, List

from src.risk_management.base.base_violation import BaseViolation, ViolationLevel


class RuleViolation(BaseViolation):
    """具体规则违规实现"""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        level: ViolationLevel,
        message: str,
        details: Dict[str, Any] = None,
    ):
        super().__init__(rule_id, rule_name, level, message, details)


class RuleResult:
    """规则执行结果"""

    def __init__(self):
        self._passed: bool = True
        self._violations: List[RuleViolation] = []
        self._fired_rules: int = 0

    def set_passed(self, passed: bool) -> None:
        """设置是否通过"""
        self._passed = passed

    def add_violation(self, violation: RuleViolation) -> None:
        """添加违规"""
        self._violations.append(violation)
        # 只要有违规且是阻断级别，结果就是不通过
        if violation.is_blocking():
            self._passed = False

    def set_fired_rules(self, count: int) -> None:
        """设置触发的规则数量"""
        self._fired_rules = count

    def passed(self) -> bool:
        """检查是否全部通过"""
        return self._passed

    def get_violations(self) -> List[RuleViolation]:
        """获取所有违规"""
        return self._violations

    def get_blocking_violations(self) -> List[RuleViolation]:
        """获取所有阻断级别的违规"""
        return [v for v in self._violations if v.is_blocking()]

    def get_warning_violations(self) -> List[RuleViolation]:
        """获取所有警告级别的违规"""
        return [v for v in self._violations if not v.is_blocking()]

    def has_violations(self) -> bool:
        """检查是否有违规"""
        return len(self._violations) > 0

    def fired_rules_count(self) -> int:
        """获取触发的规则数量"""
        return self._fired_rules

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "passed": self._passed,
            "violations": [v.to_dict() for v in self._violations],
            "fired_rules": self._fired_rules,
        }
