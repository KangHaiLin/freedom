"""
策略存储
持久化存储策略元数据和版本
"""
from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime

from .strategy_metadata import StrategyMetadata, StrategyVersion
from src.strategy_research.base import StrategyStatus


class StrategyStorage:
    """策略文件存储"""

    def __init__(self, storage_dir: str = "data/strategies"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._storage_dir / "index.json"
        self._cache: Dict[str, StrategyMetadata] = {}
        self._load_index()

    def _load_index(self) -> None:
        """加载索引"""
        if self._index_file.exists():
            with open(self._index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    versions = [
                        StrategyVersion(
                            version_id=v['version_id'],
                            strategy_id=v['strategy_id'],
                            version_code=v['version_code'],
                            params=v['params'],
                            created_at=datetime.fromisoformat(v['created_at']),
                            created_by=v['created_by'],
                            change_note=v['change_note'],
                            is_active=v['is_active'],
                        )
                        for v in item['versions']
                    ]
                    metadata = StrategyMetadata(
                        strategy_id=item['strategy_id'],
                        strategy_name=item['strategy_name'],
                        strategy_class_path=item['strategy_class_path'],
                        description=item['description'],
                        author=item['author'],
                        status=StrategyStatus(item['status']),
                        created_at=datetime.fromisoformat(item['created_at']),
                        updated_at=datetime.fromisoformat(item['updated_at']),
                        versions=versions,
                        current_version=item['current_version'],
                        tags=item['tags'],
                        extra=item.get('extra', {}),
                    )
                    self._cache[metadata.strategy_id] = metadata

    def _save_index(self) -> None:
        """保存索引"""
        data = [m.to_dict() for m in self._cache.values()]
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_strategies(self) -> List[StrategyMetadata]:
        """列出所有策略"""
        return list(self._cache.values())

    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """获取策略"""
        return self._cache.get(strategy_id)

    def add_strategy(self, metadata: StrategyMetadata) -> bool:
        """添加策略"""
        if metadata.strategy_id in self._cache:
            return False
        self._cache[metadata.strategy_id] = metadata
        self._save_index()
        return True

    def update_strategy(self, metadata: StrategyMetadata) -> bool:
        """更新策略"""
        if metadata.strategy_id not in self._cache:
            return False
        self._cache[metadata.strategy_id] = metadata
        metadata.updated_at = datetime.now()
        self._save_index()
        return True

    def add_version(
        self,
        strategy_id: str,
        version: StrategyVersion,
    ) -> bool:
        """添加新版本"""
        metadata = self.get_strategy(strategy_id)
        if metadata is None:
            return False
        # 停用旧版本
        for v in metadata.versions:
            v.is_active = False
        version.is_active = True
        metadata.versions.append(version)
        metadata.current_version = version.version_id
        metadata.updated_at = datetime.now()
        self._save_index()
        return True

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        if strategy_id not in self._cache:
            return False
        del self._cache[strategy_id]
        self._save_index()
        return True

    def count(self) -> int:
        """获取策略总数"""
        return len(self._cache)
