"""
策略管理器
统一入口，管理策略的增删改查、版本切换
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.strategy_research.base import BaseStrategy, StrategyStatus

from .strategy_loader import StrategyLoader
from .strategy_metadata import StrategyMetadata, StrategyVersion
from .strategy_storage import StrategyStorage


class StrategyManager:
    """
    策略管理器
    管理策略元数据、版本、动态加载策略实例
    """

    def __init__(
        self,
        storage_dir: str = "data/strategies",
        strategy_dir: str = "strategies",
    ):
        self._storage = StrategyStorage(storage_dir)
        self._loader = StrategyLoader(strategy_dir)

    def create_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        strategy_class_path: str,
        description: str,
        author: str,
        params: Dict,
        tags: Optional[List[str]] = None,
        created_by: int = 0,
        change_note: str = "初始版本",
    ) -> Tuple[bool, str, Optional[StrategyMetadata]]:
        """
        创建新策略

        Returns:
            (success, message, metadata)
        """
        if self._storage.get_strategy(strategy_id):
            return False, f"Strategy {strategy_id} already exists", None

        # 创建初始版本
        version = StrategyVersion(
            version_id=1,
            strategy_id=strategy_id,
            version_code="1.0.0",
            params=params,
            created_at=datetime.now(),
            created_by=created_by,
            change_note=change_note,
            is_active=True,
        )

        metadata = StrategyMetadata(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_class_path=strategy_class_path,
            description=description,
            author=author,
            status=StrategyStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            versions=[version],
            current_version=1,
            tags=tags or [],
            extra={},
        )

        success = self._storage.add_strategy(metadata)
        if success:
            return True, "Created", metadata
        return False, "Failed to save", None

    def create_new_version(
        self,
        strategy_id: str,
        version_code: str,
        params: Dict,
        created_by: int = 0,
        change_note: str = "",
    ) -> Tuple[bool, str, Optional[StrategyVersion]]:
        """
        创建新版本

        Returns:
            (success, message, version)
        """
        metadata = self._storage.get_strategy(strategy_id)
        if metadata is None:
            return False, f"Strategy {strategy_id} not found", None

        next_version_id = len(metadata.versions) + 1
        version = StrategyVersion(
            version_id=next_version_id,
            strategy_id=strategy_id,
            version_code=version_code,
            params=params,
            created_at=datetime.now(),
            created_by=created_by,
            change_note=change_note,
            is_active=True,
        )

        success = self._storage.add_version(strategy_id, version)
        if success:
            return True, "Version added", version
        return False, "Failed to add version", None

    def activate_version(
        self,
        strategy_id: str,
        version_id: int,
    ) -> bool:
        """激活指定版本"""
        metadata = self._storage.get_strategy(strategy_id)
        if metadata is None:
            return False

        for v in metadata.versions:
            v.is_active = v.version_id == version_id

        metadata.current_version = version_id
        metadata.updated_at = datetime.now()
        self._storage.update_strategy(metadata)
        return True

    def update_status(
        self,
        strategy_id: str,
        status: StrategyStatus,
    ) -> bool:
        """更新策略状态"""
        metadata = self._storage.get_strategy(strategy_id)
        if metadata is None:
            return False

        metadata.status = status
        metadata.updated_at = datetime.now()
        self._storage.update_strategy(metadata)
        return True

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        return self._storage.delete_strategy(strategy_id)

    def get_metadata(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """获取策略元数据"""
        return self._storage.get_strategy(strategy_id)

    def list_strategies(
        self,
        status: Optional[StrategyStatus] = None,
        tag: Optional[str] = None,
    ) -> List[StrategyMetadata]:
        """列出策略"""
        all_strategies = self._storage.list_strategies()

        if status is not None:
            all_strategies = [s for s in all_strategies if s.status == status]

        if tag is not None:
            all_strategies = [s for s in all_strategies if tag in s.tags]

        return all_strategies

    def instantiate(self, strategy_id: str) -> Optional[BaseStrategy]:
        """实例化策略，使用当前激活版本参数"""
        metadata = self._storage.get_strategy(strategy_id)
        if metadata is None:
            return None

        active_version = metadata.current_active_version
        if active_version is None:
            return None

        instance = self._loader.create_instance(
            metadata.strategy_class_path,
            active_version.params,
        )

        if instance is not None:
            instance.strategy_name = metadata.strategy_name
            instance.params = active_version.params

        return instance

    def instantiate_with_version(
        self,
        strategy_id: str,
        version_id: int,
    ) -> Optional[BaseStrategy]:
        """使用指定版本实例化策略"""
        metadata = self._storage.get_strategy(strategy_id)
        if metadata is None:
            return None

        version = next((v for v in metadata.versions if v.version_id == version_id), None)
        if version is None:
            return None

        instance = self._loader.create_instance(
            metadata.strategy_class_path,
            version.params,
        )

        if instance:
            instance.strategy_name = metadata.strategy_name
            instance.params = version.params

        return instance

    def count(self) -> int:
        """获取策略总数"""
        return self._storage.count()

    def health_check(self) -> Dict:
        """健康检查"""
        return {
            "status": "ok",
            "total_strategies": self.count(),
            "storage_dir": str(self._storage._storage_dir),
        }
