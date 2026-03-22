"""
数据处理器抽象基类
所有数据处理器都需要继承此基类，实现统一的处理接口
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from common.exceptions import DataException
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """数据处理器抽象基类"""

    def __init__(self, name: str = None, config: Dict = None):
        """
        初始化处理器
        Args:
            name: 处理器名称，默认使用类名
            config: 配置字典
        """
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.process_count = 0
        self.total_processing_time = 0.0

    @abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """
        执行数据处理
        Args:
            data: 输入数据，可以是DataFrame、dict或其他格式
            **kwargs: 其他处理参数
        Returns:
            处理后的数据
        """
        pass

    def validate_input(self, data: Any) -> bool:
        """
        验证输入数据有效性
        Args:
            data: 输入数据
        Returns:
            是否有效
        """
        if data is None:
            logger.warning(f"{self.name}: 输入数据为空")
            return False

        # 如果是DataFrame，检查是否为空
        if isinstance(data, pd.DataFrame) and data.empty:
            logger.warning(f"{self.name}: 输入DataFrame为空")
            return False

        # 如果是numpy数组，检查长度
        if isinstance(data, np.ndarray) and len(data) == 0:
            logger.warning(f"{self.name}: 输入数组为空")
            return False

        return True

    def get_processor_info(self) -> Dict:
        """
        获取处理器信息
        Returns:
            处理器信息字典
        """
        avg_time = self.total_processing_time / self.process_count if self.process_count > 0 else 0
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "enabled": self.enabled,
            "process_count": self.process_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_time,
            "config": self.config,
        }

    def _record_processing(self, start_time: float):
        """记录处理时间"""
        processing_time = time.time() - start_time
        self.process_count += 1
        self.total_processing_time += processing_time

    def health_check(self) -> Dict:
        """
        健康检查
        Returns:
            健康状态
        """
        avg_time = self.total_processing_time / self.process_count if self.process_count > 0 else 0
        return {
            "name": self.name,
            "status": "healthy" if self.enabled else "disabled",
            "process_count": self.process_count,
            "average_processing_time_ms": avg_time * 1000,
            "check_time": DateTimeUtils.now_str(),
        }

    def enable(self):
        """启用处理器"""
        self.enabled = True
        logger.info(f"{self.name}: 处理器已启用")

    def disable(self):
        """禁用处理器"""
        self.enabled = False
        logger.info(f"{self.name}: 处理器已禁用")
