"""
配置中心 - 配置管理器
统一入口，单例模式，支持热更新，配置变更监听
"""
import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from pathlib import Path
from .base_config import ConfigSource
from .config_provider import ConfigProvider
from .file_config import FileConfigSource
from .env_config import EnvConfigSource

T = TypeVar('T')


class ConfigManager:
    """
    配置管理器
    统一配置入口，支持多源配置，热更新，变更监听
    单例模式，全局唯一实例
    """

    _instance: Optional['ConfigManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'ConfigManager':
        """单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化，只执行一次"""
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._provider = ConfigProvider()
        self._change_listeners: list[Callable[[str, Any, Any], None]] = []
        self._hot_reload_enabled = False
        self._hot_reload_thread: Optional[threading.Thread] = None
        self._hot_reload_stop = threading.Event()

    def initialize(
        self,
        config_file: Optional[str | Path] = None,
        env_prefix: str = "QUANT_",
        enable_hotreload: bool = True,
    ) -> None:
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
            env_prefix: 环境变量前缀
            enable_hotreload: 是否启用热重载
        """
        # 添加环境变量（高优先级）
        env_source = EnvConfigSource(prefix=env_prefix)
        self._provider.add_source(env_source, priority=100)

        # 添加文件配置（中优先级）
        if config_file is not None and Path(config_file).exists():
            file_source = FileConfigSource(
                config_path=config_file,
                watch_changes=enable_hotreload,
            )
            # 注册变更回调
            file_source.on_change(self._on_source_change)
            self._provider.add_source(file_source, priority=50)

        self._hot_reload_enabled = enable_hotreload

        # 启动热重载后台线程
        if enable_hotreload and config_file is not None:
            self._start_hot_reload()

    def _start_hot_reload(self) -> None:
        """启动热重载线程"""
        self._hot_reload_stop.clear()
        self._hot_reload_thread = threading.Thread(
            target=self._hot_reload_loop,
            daemon=True
        )
        self._hot_reload_thread.start()

    def _hot_reload_loop(self) -> None:
        """热重载循环"""
        while not self._hot_reload_stop.is_set():
            self.reload()
            self._hot_reload_stop.wait(5.0)  # 每 5 秒检查一次

    def _stop_hot_reload(self) -> None:
        """停止热重载线程"""
        if self._hot_reload_thread is not None:
            self._hot_reload_stop.set()
            self._hot_reload_thread.join(timeout=2.0)
            self._hot_reload_thread = None

    def _on_source_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """处理配置源变更"""
        # 通知所有监听器
        for listener in self._change_listeners:
            try:
                listener(key, old_value, new_value)
            except Exception:
                pass

    def add_source(self, source: ConfigSource, priority: int = 0) -> 'ConfigManager':
        """添加配置源"""
        source.on_change(self._on_source_change)
        self._provider.add_source(source, priority)
        return self

    def get(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> Optional[T]:
        """获取配置值"""
        return self._provider.get(key, default, expected_type)

    def get_required(self, key: str, expected_type: Optional[Type[T]] = None) -> T:
        """获取必须的配置值"""
        return self._provider.get_required(key, expected_type)

    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        return self._provider.set(key, value)

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return self._provider.has(key)

    def reload(self) -> None:
        """重新加载所有配置"""
        self._provider.reload_all()

    def watch_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """添加配置变更监听器"""
        self._change_listeners.append(callback)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._provider.get_all()

    @property
    def hot_reload_enabled(self) -> bool:
        """是否启用热重载"""
        return self._hot_reload_enabled

    def shutdown(self) -> None:
        """关闭配置管理器，停止后台线程"""
        self._stop_hot_reload()


# 全局实例
def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return ConfigManager()
