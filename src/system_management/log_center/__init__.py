"""
日志中心
负责结构化日志收集、存储、查询，支持多处理器输出
"""
from .base_logger import BaseLogger, LogLevel, LogRecord
from .console_logger import ConsoleLogger
from .file_logger import FileLogger
from .structured_logger import StructuredLogger
from .log_manager import LogManager, ModuleLogger, get_log_manager, get_logger

__all__ = [
    'BaseLogger',
    'LogLevel',
    'LogRecord',
    'ConsoleLogger',
    'FileLogger',
    'StructuredLogger',
    'LogManager',
    'ModuleLogger',
    'get_log_manager',
    'get_logger',
]
