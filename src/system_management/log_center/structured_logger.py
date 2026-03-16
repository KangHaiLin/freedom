"""
日志中心 - JSON结构化日志处理器
支持包含上下文信息和trace_id链路追踪
"""
import json
from typing import Optional, IO
from pathlib import Path
from .base_logger import BaseLogger, LogLevel, LogRecord


class StructuredLogger(BaseLogger):
    """
    JSON 结构化日志处理器
    每条日志输出为一行 JSON，方便日志分析工具处理
    支持 trace_id 用于链路追踪
    """

    def __init__(
        self,
        output_file: Optional[str | Path] = None,
        min_level: LogLevel = LogLevel.DEBUG,
        ensure_ascii: bool = False,
    ):
        """
        初始化结构化日志处理器

        Args:
            output_file: 输出文件路径，如果为 None 输出到 stdout
            min_level: 最小日志级别
            ensure_ascii: 是否确保 ASCII 输出
        """
        super().__init__(min_level)
        self.ensure_ascii = ensure_ascii
        self._file: Optional[IO] = None
        self._close_on_exit: bool = False

        if output_file is not None:
            output_path = Path(output_file).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(output_path, 'a', encoding='utf-8')
            self._close_on_exit = True
        else:
            import sys
            self._file = sys.stdout

    def log(self, record: LogRecord) -> None:
        """记录结构化日志"""
        if not self.should_log(record.level):
            return

        log_dict = record.to_dict()

        # 转换为 JSON 字符串
        json_line = json.dumps(
            log_dict,
            ensure_ascii=self.ensure_ascii,
            separators=(',', ':'),
        )

        # 写入一行
        if self._file is not None:
            self._file.write(json_line + '\n')
            self._file.flush()

    def __del__(self):
        """析构时关闭文件"""
        if self._close_on_exit and self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass
