"""
规则数据类
存储规则元数据和可执行逻辑
"""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from src.risk_management.base.base_rule import BaseRule, RuleLevel


class Rule(BaseRule):
    """
    具体规则实现
    支持函数式定义规则，便于动态加载
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_group: str,
        check_func: Callable[[Dict[str, Any]], bool],
        message_func: Callable[[Dict[str, Any]], str],
        details_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        level: RuleLevel = RuleLevel.WARNING,
        enabled: bool = True,
        priority: int = 1,
        description: Optional[str] = None,
    ):
        """
        初始化规则

        Args:
            rule_id: 规则ID
            rule_name: 规则名称
            rule_group: 规则组
            check_func: 检查函数，接收context返回True(通过)/False(违规)
            message_func: 获取违规信息函数
            details_func: 获取违规详情函数，可选
            level: 规则级别
            enabled: 是否启用
            priority: 优先级
            description: 描述
        """
        super().__init__(
            rule_id=rule_id,
            rule_name=rule_name,
            rule_group=rule_group,
            level=level,
            enabled=enabled,
            priority=priority,
            description=description,
        )
        self._check_func = check_func
        self._message_func = message_func
        self._details_func = details_func

    def check(self, context: Dict[str, Any]) -> bool:
        """执行规则检查"""
        if not self.enabled:
            return True
        return self._check_func(context)

    def get_violation_message(self, context: Dict[str, Any]) -> str:
        """获取违规信息"""
        return self._message_func(context)

    def get_violation_details(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取违规详情"""
        if self._details_func:
            return self._details_func(context)
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """从字典创建规则 - 反序列化"""
        # 注意：函数无法序列化，此方法用于从数据库加载规则，需要重新绑定函数
        # 动态加载规则需要从规则内容重新编译函数
        level = RuleLevel(data.get("level", "warning"))
        return cls(
            rule_id=data["rule_id"],
            rule_name=data["rule_name"],
            rule_group=data["rule_group"],
            check_func=lambda ctx: False,  # 需要重新绑定
            message_func=lambda ctx: data.get("description", ""),
            level=level,
            enabled=data.get("enabled", True),
            priority=data.get("priority", 1),
            description=data.get("description"),
        )


class RuleVersion:
    """
    规则版本
    支持版本管理和回滚
    """

    def __init__(
        self,
        version_id: str,
        rule_id: str,
        rule_content: str,
        rule_group: str,
        created_by: int,
        gray_percentage: int = 0,
        gray_users: Optional[list] = None,
    ):
        self.version_id = version_id
        self.rule_id = rule_id
        self.rule_content = rule_content
        self.rule_group = rule_group
        self.created_by = created_by
        self.created_at = datetime.now()
        self.gray_percentage = gray_percentage
        self.gray_users = gray_users or []

    def is_gray(self) -> bool:
        """是否是灰度版本"""
        return self.gray_percentage > 0 or len(self.gray_users) > 0

    def matches_user(self, user_id: int) -> bool:
        """检查此版本是否应该对该用户生效"""
        if not self.is_gray():
            return True
        if user_id in self.gray_users:
            return True
        if self.gray_percentage > 0:
            # 使用用户ID哈希判断是否命中灰度
            return abs(hash(user_id) % 100) < self.gray_percentage
        return False

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "version_id": self.version_id,
            "rule_id": self.rule_id,
            "rule_content": self.rule_content,
            "rule_group": self.rule_group,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "gray_percentage": self.gray_percentage,
            "gray_users": self.gray_users,
        }
