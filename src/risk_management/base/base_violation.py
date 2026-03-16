"""
违规结果抽象基类
定义风险违规结果的统一接口
"""
from abc import ABC
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class ViolationLevel(Enum):
    """违规级别"""
    INFO = "info"          # 信息提示
    WARNING = "warning"    # 警告
    ERROR = "error"        # 错误，交易被拒绝
    CRITICAL = "critical"  # 严重违规，需要立即处理


class BaseViolation(ABC):
    """违规结果抽象基类
    存储规则检查发现的违规信息
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        level: ViolationLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化违规结果

        Args:
            rule_id: 触发违规的规则ID
            rule_name: 规则名称
            level: 违规级别
            message: 违规描述信息
            details: 违规详情数据
        """
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.level = level
        self.message = message
        self.details = details or {}
        self.occurred_at = datetime.now()

    def is_blocking(self) -> bool:
        """检查此违规是否应该阻断交易"""
        return self.level in [ViolationLevel.ERROR, ViolationLevel.CRITICAL]

    def should_alert(self) -> bool:
        """检查此违规是否应该生成告警"""
        return self.level in [ViolationLevel.WARNING, ViolationLevel.ERROR, ViolationLevel.CRITICAL]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'occurred_at': self.occurred_at.isoformat(),
        }
