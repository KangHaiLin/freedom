"""
日志中心 - 日志处理器抽象基类
定义日志处理器的基础接口和日志级别
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional


class LogLevel(IntEnum):
    """日志级别定义"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def from_string(cls, level_str: str) -> 'LogLevel':
        """从字符串转换日志级别"""
        level_map = {
            'debug': cls.DEBUG,
            'info': cls.INFO,
            'warning': cls.WARNING,
            'warn': cls.WARNING,
            'error': cls.ERROR,
            'critical': cls.CRITICAL,
            'fatal': cls.CRITICAL,
        }
        return level_map.get(level_str.lower(), cls.INFO)


@dataclass
class LogRecord:
    """日志记录"""
    level: LogLevel
    message: str
    module: str
    timestamp: float
    context: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'level': self.level.name,
            'level_value': self.level.value,
            'message': self.message,
            'module': self.module,
            'timestamp': self.timestamp,
        }
        if self.context:
            result['context'] = self.context
        if self.trace_id:
            result['trace_id'] = self.trace_id
        return result


class BaseLogger(ABC):
    """日志处理器抽象基类"""

    def __init__(self, min_level: LogLevel = LogLevel.DEBUG):
        """初始化"""
        self.min_level = min_level

    def should_log(self, level: LogLevel) -> bool:
        """检查是否应该记录该级别日志"""
        return level >= self.min_level

    @abstractmethod
    def log(self, record: LogRecord) -> None:
        """
        记录日志

        Args:
            record: 日志记录
        """
        pass

    def set_min_level(self, level: LogLevel) -> None:
        """设置最小日志级别"""
        self.min_level = level
