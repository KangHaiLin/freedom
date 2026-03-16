"""
监控中心 - 监控抽象基类
定义监控收集器的基础接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseMonitor(ABC):
    """监控抽象基类"""

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        收集当前指标

        Returns:
            指标字典，键为指标名，值为指标值
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取最近收集到的指标

        Returns:
            指标字典
        """
        pass

    @property
    def name(self) -> str:
        """监控器名称"""
        return self.__class__.__name__
