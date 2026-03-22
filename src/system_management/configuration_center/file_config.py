"""
配置中心 - 文件配置源
支持 YAML 和 JSON 配置文件，支持热重载
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from .base_config import ConfigSource


class FileConfigSource(ConfigSource):
    """文件配置源，支持 YAML 和 JSON 格式"""

    def __init__(
        self,
        config_path: str | Path,
        watch_changes: bool = False,
        reload_interval: float = 5.0,
    ):
        """
        初始化文件配置源

        Args:
            config_path: 配置文件路径
            watch_changes: 是否监听文件变更自动重载
            reload_interval: 重载检查间隔（秒）
        """
        self.config_path = Path(config_path).resolve()
        self.watch_changes = watch_changes
        self.reload_interval = reload_interval
        self._cache: Dict[str, Any] = {}
        self._last_modified: float = 0.0
        self._change_callbacks: list[Callable[[str, Any, Any], None]] = []
        self._last_check: float = 0.0

        # 初始加载
        self.load()

    def _detect_format(self) -> str:
        """检测文件格式"""
        suffix = self.config_path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            return "yaml"
        elif suffix in (".json"):
            return "json"
        else:
            # 默认尝试 yaml
            return "yaml"

    def _load_file(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()

        fmt = self._detect_format()
        if fmt == "yaml":
            data = yaml.safe_load(content) or {}
        elif fmt == "json":
            data = json.loads(content)
        else:
            data = {}

        # 扁平化嵌套字典，用点分隔键名
        return self._flatten_dict(data)

    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """将嵌套字典扁平化"""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, full_key))
            else:
                result[full_key] = value
        return result

    def check_reload(self) -> bool:
        """检查是否需要重载"""
        if not self.config_path.exists():
            return False

        current_mtime = os.path.getmtime(self.config_path)

        # 如果文件修改时间变化，需要重载
        if current_mtime != self._last_modified:
            old_cache = self._cache.copy()
            self.load()
            # 触发变更回调
            self._notify_changes(old_cache, self._cache)
            return True

        return False

    def load(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_path.exists():
            self._last_modified = os.path.getmtime(self.config_path)
        self._cache = self._load_file()
        return self._cache.copy()

    def get(self, key: str) -> Optional[Any]:
        """获取配置值"""
        # 如果开启了变更监听，定期检查
        if self.watch_changes:
            self.check_reload()
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> bool:
        """设置配置值并保存回文件"""
        # 先获取当前完整嵌套结构
        full_data = self._unflatten_dict(self._cache)
        self._set_nested(full_data, key.split("."), value)
        self._cache[key] = value

        # 写入文件
        try:
            fmt = self._detect_format()
            with open(self.config_path, "w", encoding="utf-8") as f:
                if fmt == "yaml":
                    yaml.dump(full_data, f, default_flow_style=False, allow_unicode=True)
                elif fmt == "json":
                    json.dump(full_data, f, indent=2, ensure_ascii=False)
            self._last_modified = os.path.getmtime(self.config_path)
            return True
        except Exception:
            return False

    def _unflatten_dict(self, flat: Dict[str, Any]) -> Dict[str, Any]:
        """将扁平化字典还原为嵌套字典"""
        result = {}
        for key, value in flat.items():
            parts = key.split(".")
            current = result
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result

    def _set_nested(self, data: Dict[str, Any], keys: list[str], value: Any) -> None:
        """在嵌套字典中设置值"""
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return key in self._cache

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """注册配置变更回调"""
        self._change_callbacks.append(callback)

    def _notify_changes(self, old_cache: Dict[str, Any], new_cache: Dict[str, Any]) -> None:
        """通知配置变更"""
        for key, new_value in new_cache.items():
            old_value = old_cache.get(key)
            if old_value != new_value:
                for callback in self._change_callbacks:
                    try:
                        callback(key, old_value, new_value)
                    except Exception:
                        pass

        for key in old_cache:
            if key not in new_cache:
                for callback in self._change_callbacks:
                    try:
                        callback(key, old_cache[key], None)
                    except Exception:
                        pass
