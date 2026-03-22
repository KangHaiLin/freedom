"""
数据处理结果封装类
统一封装处理结果，包含处理状态、消息、指标统计等信息
"""

from typing import Any, Dict, Optional

import pandas as pd

from common.utils import DateTimeUtils


class ProcessingResult:
    """数据处理结果封装"""

    def __init__(
        self,
        processor_name: str,
        success: bool,
        message: str = "",
        data: Any = None,
        metrics: Optional[Dict[str, Any]] = None,
        processing_time: float = 0.0,
    ):
        """
        初始化处理结果
        Args:
            processor_name: 处理器名称
            success: 是否处理成功
            message: 处理消息
            data: 处理后的数据
            metrics: 处理指标统计
            processing_time: 处理耗时（秒）
        """
        self.processor_name = processor_name
        self.success = success
        self.message = message
        self.data = data
        self.metrics = metrics or {}
        self.processing_time = processing_time
        self.timestamp = DateTimeUtils.now()

    @classmethod
    def success(
        cls,
        processor_name: str,
        data: Any = None,
        metrics: Dict = None,
        message: str = "",
        processing_time: float = 0.0,
    ) -> "ProcessingResult":
        """创建成功的处理结果"""
        return cls(
            processor_name=processor_name,
            success=True,
            message=message or "处理成功",
            data=data,
            metrics=metrics,
            processing_time=processing_time,
        )

    @classmethod
    def failure(
        cls, processor_name: str, message: str = "", metrics: Dict = None, processing_time: float = 0.0
    ) -> "ProcessingResult":
        """创建失败的处理结果"""
        return cls(
            processor_name=processor_name,
            success=False,
            message=message or "处理失败",
            data=None,
            metrics=metrics,
            processing_time=processing_time,
        )

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        data_info = {}
        if self.data is not None:
            if isinstance(self.data, pd.DataFrame):
                data_info = {"type": "DataFrame", "rows": len(self.data), "columns": list(self.data.columns)}
            elif isinstance(self.data, list):
                data_info = {"type": "list", "length": len(self.data)}
            elif isinstance(self.data, dict):
                data_info = {"type": "dict", "keys": list(self.data.keys())}
            else:
                data_info = {"type": self.data.__class__.__name__}

        return {
            "processor_name": self.processor_name,
            "success": self.success,
            "message": self.message,
            "data_info": data_info,
            "metrics": self.metrics,
            "processing_time": self.processing_time,
            "timestamp": DateTimeUtils.to_str(self.timestamp),
        }

    def get_data(self) -> Any:
        """获取处理后的数据"""
        return self.data

    def is_success(self) -> bool:
        """检查是否处理成功"""
        return self.success
