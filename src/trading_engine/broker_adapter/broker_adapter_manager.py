"""
券商适配器管理器
管理多个券商适配器，提供统一访问入口
"""
from typing import Dict, Any, Optional
import logging

from src.trading_engine.base.base_broker_adapter import BaseBrokerAdapter

logger = logging.getLogger(__name__)


class BrokerAdapterManager:
    """券商适配器管理器，统一管理多个券商适配器"""

    def __init__(self):
        """初始化"""
        self._adapters: Dict[str, BaseBrokerAdapter] = {}
        self._default_adapter: Optional[str] = None

    def register_adapter(self, name: str, adapter: BaseBrokerAdapter, default: bool = False) -> None:
        """
        注册券商适配器
        Args:
            name: 适配器名称
            adapter: 适配器实例
            default: 是否设为默认
        """
        self._adapters[name] = adapter
        if default or self._default_adapter is None:
            self._default_adapter = name
        logger.info(f"注册券商适配器: {name}, default={default}")

    def get_adapter(self, name: Optional[str] = None) -> Optional[BaseBrokerAdapter]:
        """
        获取券商适配器
        Args:
            name: 适配器名称，None获取默认
        Returns:
            适配器实例
        """
        if name is None:
            name = self._default_adapter
        if name is None:
            return None
        return self._adapters.get(name)

    def get_default_adapter(self) -> Optional[BaseBrokerAdapter]:
        """获取默认适配器"""
        return self.get_adapter()

    def unregister_adapter(self, name: str) -> bool:
        """
        注销券商适配器
        Args:
            name: 适配器名称
        Returns:
            是否注销成功
        """
        if name in self._adapters:
            adapter = self._adapters[name]
            if adapter.is_connected():
                adapter.disconnect()
            del self._adapters[name]
            if name == self._default_adapter:
                self._default_adapter = next(iter(self._adapters.keys())) if self._adapters else None
            logger.info(f"注销券商适配器: {name}")
            return True
        return False

    def connect_all(self) -> Dict[str, bool]:
        """连接所有适配器"""
        results = {}
        for name, adapter in self._adapters.items():
            if not adapter.is_connected():
                results[name] = adapter.connect()
            else:
                results[name] = True
        return results

    def disconnect_all(self) -> None:
        """断开所有适配器"""
        for adapter in self._adapters.values():
            if adapter.is_connected():
                adapter.disconnect()

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """健康检查所有适配器"""
        results = {}
        for name, adapter in self._adapters.items():
            results[name] = adapter.health_check()
        return results

    def get_adapter_names(self) -> list:
        """获取所有已注册适配器名称"""
        return list(self._adapters.keys())

    @property
    def default_adapter_name(self) -> Optional[str]:
        """获取默认适配器名称"""
        return self._default_adapter
