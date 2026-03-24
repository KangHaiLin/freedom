"""
日志中心 - 控制台日志处理器
支持彩色输出，格式化显示
"""

import sys
from datetime import datetime

from .base_logger import BaseLogger, LogLevel, LogRecord


class ConsoleLogger(BaseLogger):
    """控制台日志处理器，支持彩色输出"""

    # ANSI 颜色代码
    COLORS = {
        LogLevel.DEBUG: "\033[37m",  # 灰色
        LogLevel.INFO: "\033[32m",  # 绿色
        LogLevel.WARNING: "\033[33m",  # 黄色
        LogLevel.ERROR: "\033[31m",  # 红色
        LogLevel.CRITICAL: "\033[35;1m",  # 紫红色加粗
    }
    RESET = "\033[0m"

    def __init__(
        self,
        min_level: LogLevel = LogLevel.DEBUG,
        enable_color: bool = True,
        show_timestamp: bool = True,
        show_module: bool = True,
    ):
        """
        初始化控制台日志处理器

        Args:
            min_level: 最小日志级别
            enable_color: 是否启用彩色输出
            show_timestamp: 是否显示时间戳
            show_module: 是否显示模块名
        """
        super().__init__(min_level)
        self.enable_color = enable_color and sys.stdout.isatty()
        self.show_timestamp = show_timestamp
        self.show_module = show_module

    def _get_color(self, level: LogLevel) -> str:
        """获取颜色代码"""
        if not self.enable_color:
            return ""
        return self.COLORS.get(level, "")

    def log(self, record: LogRecord) -> None:
        """记录日志到控制台"""
        if not self.should_log(record.level):
            return

        parts = []

        # 时间戳
        if self.show_timestamp:
            dt = datetime.fromtimestamp(record.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            parts.append(f"[{time_str}]")

        # 级别
        color = self._get_color(record.level)
        level_str = f"{record.level.name:<5}"
        parts.append(f"[{level_str}]")

        # 模块
        if self.show_module and record.module:
            parts.append(f"[{record.module}]")

        # 消息
        message = record.message
        if record.context:
            context_str = " ".join(f"{k}={v}" for k, v in record.context.items())
            message = f"{message} {context_str}"

        # 组合输出
        output = " ".join(parts) + " " + message

        if self.enable_color:
            output = f"{color}{output}{self.RESET}"

        # 输出到控制台
        print(output)
