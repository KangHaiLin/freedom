"""
规则抽象基类
定义风控规则的统一接口
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class RuleLevel(Enum):
    """规则级别 - 决定违规时的处理方式"""
    INFO = "info"          # 仅提示信息
    WARNING = "warning"    # 警告，允许交易但告警
    ERROR = "error"        # 错误，拒绝交易
    BLOCK = "block"        # 拦截，严重违规阻断交易


class RuleType(Enum):
    """规则类型"""
    PRE_TRADE = "pre_trade"        # 交易前检查
    INTRA_DAY = "intra_day"        # 盘中监控
    COMPLIANCE = "compliance"      # 合规检查
    POSITION = "position"          # 持仓风险
    MARKET = "market"              # 市场风险
    OPERATION = "operation"        # 操作风险


class BaseRule(ABC):
    """规则抽象基类
    所有具体风控规则都必须继承此类
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_group: str,
        level: RuleLevel = RuleLevel.WARNING,
        enabled: bool = True,
        priority: int = 1,
        description: Optional[str] = None,
    ):
        """
        初始化规则

        Args:
            rule_id: 规则ID，唯一标识
            rule_name: 规则名称
            rule_group: 规则组（pre_trade/intra_day/compliance等）
            level: 规则级别，决定违规处理方式
            enabled: 是否启用
            priority: 优先级，数字越小优先级越高
            description: 规则描述
        """
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_group = rule_group
        self.level = level
        self.enabled = enabled
        self.priority = priority
        self.description = description
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @abstractmethod
    def check(self, context: Dict[str, Any]) -> bool:
        """
        执行规则检查

        Args:
            context: 检查上下文，包含订单、持仓、用户等信息

        Returns:
            True: 检查通过，False: 检查不通过（违规）
        """
        pass

    @abstractmethod
    def get_violation_message(self, context: Dict[str, Any]) -> str:
        """
        获取违规提示信息

        Args:
            context: 检查上下文

        Returns:
            违规描述信息
        """
        pass

    @abstractmethod
    def get_violation_details(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取违规详情数据

        Args:
            context: 检查上下文

        Returns:
            违规详情字典，包含当前值、限制值等
        """
        pass

    def enable(self) -> None:
        """启用规则"""
        self.enabled = True
        self.updated_at = datetime.now()

    def disable(self) -> None:
        """禁用规则"""
        self.enabled = False
        self.updated_at = datetime.now()

    def is_enabled(self) -> bool:
        """检查规则是否启用"""
        return self.enabled

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_group': self.rule_group,
            'level': self.level.value,
            'enabled': self.enabled,
            'priority': self.priority,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseRule':
        """从字典反序列化"""
        # 子类需要覆盖此方法
        raise NotImplementedError("子类必须实现 from_dict 方法")
