"""
配置中心 - 配置源抽象基类
定义配置源的基础接口
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class ConfigSource(ABC):
    """配置源抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        获取配置值

        Args:
            key: 配置键

        Returns:
            配置值，如果不存在返回 None
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            是否设置成功
        """
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        检查配置是否存在

        Args:
            key: 配置键

        Returns:
            配置是否存在
        """
        pass

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        加载所有配置

        Returns:
            所有配置键值对
        """
        pass

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        注册配置变更回调

        Args:
            callback: 回调函数，参数为 (key, old_value, new_value)
        """
        # 默认实现为空，子类可根据需要重写
        pass
