"""
日志中心 - 文件日志处理器
支持按大小和时间轮转，保留天数配置，压缩过期日志
"""

import gzip
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .base_logger import BaseLogger, LogLevel, LogRecord


class FileLogger(BaseLogger):
    """
    文件日志处理器
    支持：
    - 按大小轮转
    - 按时间轮转（每天）
    - 自动清理过期日志
    - 压缩过期日志
    """

    def __init__(
        self,
        log_file: str | Path,
        min_level: LogLevel = LogLevel.DEBUG,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 30,
        rotate_by_day: bool = True,
        compress_old_logs: bool = True,
    ):
        """
        初始化文件日志处理器

        Args:
            log_file: 日志文件路径
            min_level: 最小日志级别
            max_size_bytes: 单个文件最大大小，超过会轮转
            retention_days: 日志保留天数
            rotate_by_day: 是否按天轮转
            compress_old_logs: 是否压缩旧日志
        """
        super().__init__(min_level)
        self.log_file = Path(log_file).resolve()
        self.max_size_bytes = max_size_bytes
        self.retention_days = retention_days
        self.rotate_by_day = rotate_by_day
        self.compress_old_logs = compress_old_logs

        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 当前文件句柄
        self._file: Optional[Any] = None
        self._current_size: int = 0
        self._current_day: Optional[int] = None

        # 打开初始文件
        self._open_file()
        # 清理过期日志
        self._cleanup_old_logs()

    def _open_file(self) -> None:
        """打开日志文件"""
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass

        self._file = open(self.log_file, "a", encoding="utf-8")
        self._current_size = os.path.getsize(self.log_file) if self.log_file.exists() else 0
        self._current_day = datetime.now().day

    def _should_rotate(self) -> bool:
        """检查是否需要轮转"""
        # 按天轮转检查
        if self.rotate_by_day and datetime.now().day != self._current_day:
            return True

        # 按大小轮转检查
        if self._current_size >= self.max_size_bytes:
            return True

        return False

    def _rotate(self) -> None:
        """执行日志轮转"""
        self._file.close()

        # 生成轮转文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = self.log_file.parent / f"{self.log_file.stem}_{timestamp}{self.log_file.suffix}"

        # 重命名当前日志文件
        if self.log_file.exists() and self.log_file.stat().st_size > 0:
            shutil.move(str(self.log_file), str(rotated_path))

            # 压缩旧日志
            if self.compress_old_logs:
                with open(rotated_path, "rb") as f_in:
                    with gzip.open(f"{rotated_path}.gz", "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                rotated_path.unlink()

        # 打开新文件
        self._open_file()

        # 清理过期日志
        self._cleanup_old_logs()

    def _cleanup_old_logs(self) -> None:
        """清理过期日志"""
        if self.retention_days <= 0:
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cutoff_timestamp = cutoff.timestamp()

        # 查找所有轮转日志
        pattern = f"{self.log_file.stem}_*{self.log_file.suffix}*"
        for log_file in self.log_file.parent.glob(pattern):
            mtime = log_file.stat().st_mtime
            if mtime < cutoff_timestamp:
                try:
                    log_file.unlink()
                except Exception:
                    pass

    def log(self, record: LogRecord) -> None:
        """记录日志到文件"""
        if not self.should_log(record.level):
            return

        # 检查是否需要轮转
        if self._should_rotate():
            self._rotate()

        # 格式化日志行
        dt = datetime.fromtimestamp(record.timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_str = record.level.name
        module_str = record.module
        message = record.message

        if record.context:
            context_str = " ".join(f"{k}={v}" for k, v in record.context.items())
            line = f"{time_str} [{level_str:5}] [{module_str}] {message} {context_str}\n"
        else:
            line = f"{time_str} [{level_str:5}] [{module_str}] {message}\n"

        # 写入文件
        self._file.write(line)
        self._current_size += len(line.encode("utf-8"))

        # 自动刷新
        self._file.flush()

    def __del__(self):
        """析构时关闭文件"""
        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
