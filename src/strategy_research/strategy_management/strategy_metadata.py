"""
策略元数据
存储策略的基本信息、参数、版本信息
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.strategy_research.base import StrategyStatus


@dataclass
class StrategyVersion:
    """策略版本"""

    version_id: int
    strategy_id: str
    version_code: str  # 语义化版本 e.g. "1.0.0"
    params: Dict[str, Any]
    created_at: datetime
    created_by: int  # 创建者用户ID
    change_note: str
    is_active: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class StrategyMetadata:
    """策略元数据"""

    strategy_id: str
    strategy_name: str
    strategy_class_path: str  # 策略类完整路径 e.g. "strategies.momentum.MomentumStrategy"
    description: str
    author: str
    status: StrategyStatus
    created_at: datetime
    updated_at: datetime
    versions: list[StrategyVersion]
    current_version: Optional[int]  # 当前激活版本ID
    tags: list[str]
    extra: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["versions"] = [v.to_dict() for v in self.versions]
        return data

    @property
    def current_active_version(self) -> Optional[StrategyVersion]:
        """获取当前激活版本"""
        for v in self.versions:
            if v.is_active:
                return v
        return None
