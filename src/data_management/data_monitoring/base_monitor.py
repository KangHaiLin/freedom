"""
监控抽象基类
所有监控服务都需要继承此基类，实现统一的监控接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from enum import Enum
import logging
from datetime import datetime

from common.utils import DateTimeUtils
from common.exceptions import MonitorException

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"      # 信息级别，无需处理
    WARNING = "warning"  # 警告级别，需要关注
    ERROR = "error"    # 错误级别，需要处理
    CRITICAL = "critical"  # 严重级别，立即处理


class MonitorResult:
    """监控结果封装"""
    def __init__(
        self,
        monitor_name: str,
        success: bool,
        message: str = "",
        level: AlertLevel = AlertLevel.INFO,
        metrics: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.monitor_name = monitor_name
        self.success = success
        self.message = message
        self.level = level
        self.metrics = metrics or {}
        self.details = details or {}
        self.timestamp = DateTimeUtils.now()

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "monitor_name": self.monitor_name,
            "success": self.success,
            "message": self.message,
            "level": self.level.value,
            "metrics": self.metrics,
            "details": self.details,
            "timestamp": DateTimeUtils.to_str(self.timestamp)
        }

    def need_alert(self) -> bool:
        """是否需要发送告警"""
        return self.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]


class BaseMonitor(ABC):
    """监控抽象基类"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.interval = self.config.get('interval', 60)  # 监控间隔，秒
        self.alert_threshold = self.config.get('alert_threshold', 3)  # 连续失败N次告警
        self.failure_count = 0
        self.last_run_time: Optional[datetime] = None
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = self.config.get('alert_cooldown', 300)  # 告警冷却时间，秒

    @abstractmethod
    def run_check(self) -> MonitorResult:
        """
        执行监控检查
        Returns:
            监控结果
        """
        pass

    def run(self) -> Optional[MonitorResult]:
        """
        运行监控，包含状态管理和告警控制
        Returns:
            监控结果，如果不需要发送告警则返回None
        """
        if not self.enabled:
            return None

        try:
            self.last_run_time = DateTimeUtils.now()
            result = self.run_check()

            if result.success:
                self.failure_count = 0
            else:
                self.failure_count += 1
                logger.warning(f"监控{self.__class__.__name__}检查失败，连续失败次数：{self.failure_count}")

            # 检查是否需要告警
            if result.need_alert() and self.failure_count >= self.alert_threshold:
                if self._can_send_alert():
                    self.last_alert_time = DateTimeUtils.now()
                    return result

            return None

        except Exception as e:
            logger.error(f"监控{self.__class__.__name__}执行异常：{e}")
            self.failure_count += 1
            return MonitorResult(
                monitor_name=self.__class__.__name__,
                success=False,
                message=f"监控执行异常：{str(e)}",
                level=AlertLevel.ERROR
            )

    def _can_send_alert(self) -> bool:
        """检查是否可以发送告警（冷却时间判断）"""
        if not self.last_alert_time:
            return True
        time_since_last_alert = (DateTimeUtils.now() - self.last_alert_time).total_seconds()
        return time_since_last_alert >= self.alert_cooldown

    def get_status(self) -> Dict:
        """获取监控状态"""
        return {
            "monitor_name": self.__class__.__name__,
            "enabled": self.enabled,
            "interval": self.interval,
            "failure_count": self.failure_count,
            "last_run_time": DateTimeUtils.to_str(self.last_run_time) if self.last_run_time else None,
            "last_alert_time": DateTimeUtils.to_str(self.last_alert_time) if self.last_alert_time else None
        }
