"""
日志中心 - 日志管理器
统一入口，支持多处理器同时输出，按级别过滤
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .base_logger import BaseLogger, LogLevel, LogRecord
from .console_logger import ConsoleLogger


class LogManager:
    """
    日志管理器
    统一日志入口，支持多个日志处理器同时输出
    支持按模块过滤日志级别
    单例模式
    """

    _instance: Optional["LogManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "LogManager":
        """单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化，只执行一次"""
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._loggers: List[BaseLogger] = []
        self._module_levels: Dict[str, LogLevel] = {}
        self._trace_id: Optional[str] = None
        self._thread_local = threading.local()

        # 默认添加控制台日志
        self._loggers.append(ConsoleLogger())

    def initialize(
        self,
        level: str = "INFO",
        log_file: Optional[str] = None,
        structured_log_file: Optional[str] = None,
        enable_structured: bool = True,
        retention_days: int = 30,
    ) -> None:
        """
        初始化日志管理器

        Args:
            level: 默认日志级别
            log_file: 文件日志路径
            structured_log_file: 结构化日志路径
            enable_structured: 是否启用结构化日志
            retention_days: 日志保留天数
        """
        from .file_logger import FileLogger
        from .structured_logger import StructuredLogger

        # 清除默认处理器
        self._loggers.clear()

        # 设置默认级别
        default_level = LogLevel.from_string(level)

        # 添加控制台日志
        self._loggers.append(ConsoleLogger(min_level=default_level))

        # 添加文件日志
        if log_file is not None:
            self._loggers.append(
                FileLogger(
                    log_file=log_file,
                    min_level=default_level,
                    retention_days=retention_days,
                )
            )

        # 添加结构化日志
        if enable_structured and structured_log_file is not None:
            self._loggers.append(
                StructuredLogger(
                    output_file=structured_log_file,
                    min_level=default_level,
                )
            )

    def add_logger(self, logger: BaseLogger) -> "LogManager":
        """添加日志处理器"""
        self._loggers.append(logger)
        return self

    def set_module_level(self, module: str, level: LogLevel | str) -> None:
        """
        设置特定模块的日志级别

        Args:
            module: 模块名
            level: 日志级别
        """
        if isinstance(level, str):
            level = LogLevel.from_string(level)
        self._module_levels[module] = level

    def set_trace_id(self, trace_id: Optional[str]) -> None:
        """设置当前线程的 trace_id"""
        setattr(self._thread_local, "trace_id", trace_id)

    def get_trace_id(self) -> Optional[str]:
        """获取当前线程的 trace_id"""
        return getattr(self._thread_local, "trace_id", None)

    def _should_log(self, level: LogLevel, module: str) -> bool:
        """检查是否应该记录该日志"""
        # 检查模块特定级别
        if module in self._module_levels:
            return level >= self._module_levels[module]

        # 使用所有 logger 的最低级别
        # 如果至少有一个 logger 接受该级别，就输出
        for logger in self._loggers:
            if logger.should_log(level):
                return True
        return False

    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录日志

        Args:
            level: 日志级别
            message: 日志消息
            module: 模块名
            context: 上下文信息
        """
        if not self._should_log(level, module):
            return

        trace_id = self.get_trace_id()
        record = LogRecord(
            level=level,
            message=message,
            module=module,
            timestamp=time.time(),
            context=context,
            trace_id=trace_id,
        )

        for logger in self._loggers:
            if logger.should_log(level):
                logger.log(record)

    def debug(self, message: str, module: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        """记录 DEBUG 级别日志"""
        self.log(LogLevel.DEBUG, message, module, context)

    def info(self, message: str, module: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        """记录 INFO 级别日志"""
        self.log(LogLevel.INFO, message, module, context)

    def warning(self, message: str, module: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        """记录 WARNING 级别日志"""
        self.log(LogLevel.WARNING, message, module, context)

    def error(self, message: str, module: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        """记录 ERROR 级别日志"""
        self.log(LogLevel.ERROR, message, module, context)

    def critical(self, message: str, module: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        """记录 CRITICAL 级别日志"""
        self.log(LogLevel.CRITICAL, message, module, context)

    def get_logger(self, module: str) -> "ModuleLogger":
        """获取绑定模块名的模块日志器"""
        return ModuleLogger(self, module)


class ModuleLogger:
    """绑定模块名的日志器，方便使用"""

    def __init__(self, log_manager: LogManager, module: str):
        self._log_manager = log_manager
        self._module = module

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log_manager.debug(message, self._module, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log_manager.info(message, self._module, context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log_manager.warning(message, self._module, context)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log_manager.error(message, self._module, context)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self._log_manager.critical(message, self._module, context)


# 全局实例
def get_log_manager() -> LogManager:
    """获取全局日志管理器实例"""
    return LogManager()


def get_logger(module: str = "") -> ModuleLogger:
    """获取绑定模块的日志器"""
    return get_log_manager().get_logger(module)
