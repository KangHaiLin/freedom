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
    INFO = 0      # 信息级别，无需处理
    WARNING = 1  # 警告级别，需要关注
    ERROR = 2    # 错误级别，需要处理
    CRITICAL = 3  # 严重级别，立即处理

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    @property
    def name_lower(self):
        return self.name.lower()


class MonitorResult:
    """监控结果封装"""
    def __init__(
        self,
        monitor_name: str,
        success: bool,
        message: str = "",
        alert_level: AlertLevel = AlertLevel.INFO,
        level: AlertLevel = None,  # 兼容旧的参数名
        metrics: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.monitor_name = monitor_name
        self.success = success
        self.message = message
        # 兼容两种参数名
        self.alert_level = level if level is not None else alert_level
        self.level = self.alert_level  # 保持兼容
        self.metrics = metrics or {}
        self.details = details or {}
        self.timestamp = DateTimeUtils.now()

    @classmethod
    def success(cls, monitor_name: str, metrics: Dict = None, message: str = "") -> 'MonitorResult':
        """创建成功的监控结果"""
        return cls(
            monitor_name=monitor_name,
            success=True,
            message=message or "检查通过",
            alert_level=AlertLevel.INFO,
            metrics=metrics
        )

    @classmethod
    def failure(cls, monitor_name: str, alert_level: AlertLevel = AlertLevel.ERROR, metrics: Dict = None, message: str = "") -> 'MonitorResult':
        """创建失败的监控结果"""
        return cls(
            monitor_name=monitor_name,
            success=False,
            message=message or "检查失败",
            alert_level=alert_level,
            metrics=metrics
        )

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "monitor_name": self.monitor_name,
            "success": self.success,
            "message": self.message,
            "level": self.alert_level.name_lower,
            "level_value": self.alert_level.value,
            "metrics": self.metrics,
            "details": self.details,
            "timestamp": DateTimeUtils.to_str(self.timestamp)
        }

    def need_alert(self) -> bool:
        """是否需要发送告警"""
        return self.alert_level in [AlertLevel.ERROR, AlertLevel.CRITICAL]


class BaseMonitor(ABC):
    """监控抽象基类"""

    def __init__(self, name: str = None, config: Dict = None, check_interval: int = None, alert_cooldown: int = None, consecutive_failures_threshold: int = None):
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        # 兼容多种参数名
        self.interval = check_interval or self.config.get('interval', 60)  # 监控间隔，秒
        self.check_interval = self.interval
        self.alert_threshold = consecutive_failures_threshold or self.config.get('alert_threshold', 3)  # 连续失败N次告警
        self.consecutive_failures_threshold = self.alert_threshold
        self.failure_count = 0
        self.consecutive_failures = 0  # 兼容测试用的属性名
        self.last_run_time: Optional[datetime] = None
        self.last_alert_time: Optional[datetime] = None
        self._last_alert_time = None  # 兼容测试用的属性名
        self.alert_cooldown = alert_cooldown or self.config.get('alert_cooldown', 300)  # 告警冷却时间，秒

    @abstractmethod
    def run_check(self) -> MonitorResult:
        """
        执行监控检查
        Returns:
            监控结果
        """
        pass

    def run(self) -> MonitorResult:
        """
        运行监控，包含状态管理和告警控制
        Returns:
            监控结果对象
        """
        if not self.enabled:
            return MonitorResult.success(
                monitor_name=self.name,
                message="监控已禁用"
            )

        try:
            self.last_run_time = DateTimeUtils.now()
            result = self.run_check()

            if result.success:
                self.failure_count = 0
                self.consecutive_failures = 0
            else:
                self.failure_count += 1
                self.consecutive_failures += 1
                logger.warning(f"监控{self.name}检查失败，连续失败次数：{self.failure_count}")

            # 检查是否需要告警
            if result.need_alert() and self.failure_count >= self.alert_threshold:
                if self._can_send_alert():
                    self.last_alert_time = DateTimeUtils.now()
                    self._last_alert_time = self.last_alert_time.timestamp()
                    result.need_send_alert = True
                else:
                    result.need_send_alert = False
            else:
                result.need_send_alert = False

            return result

        except Exception as e:
            logger.error(f"监控{self.name}执行异常：{e}")
            self.failure_count += 1
            self.consecutive_failures += 1
            return MonitorResult.failure(
                monitor_name=self.name,
                alert_level=AlertLevel.ERROR,
                message=f"监控执行异常：{str(e)}"
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
            "monitor_name": self.name,
            "enabled": self.enabled,
            "interval": self.interval,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "last_run_time": DateTimeUtils.to_str(self.last_run_time) if self.last_run_time else None,
            "last_alert_time": DateTimeUtils.to_str(self.last_alert_time) if self.last_alert_time else None
        }

    def _record_success(self):
        """记录成功，重置连续失败计数"""
        self.failure_count = 0
        self.consecutive_failures = 0

    def _record_failure(self):
        """记录失败，增加连续失败计数"""
        self.failure_count += 1
        self.consecutive_failures += 1

    def _should_trigger_alert(self) -> bool:
        """是否达到告警阈值"""
        return self.consecutive_failures >= self.consecutive_failures_threshold

    def _should_send_alert(self, result: MonitorResult) -> bool:
        """是否应该发送告警"""
        # 严重告警总是发送
        if result.alert_level >= AlertLevel.CRITICAL:
            return True

        # 检查冷却时间
        if not self.last_alert_time and not self._last_alert_time:
            return True

        last_alert_time = self._last_alert_time or self.last_alert_time.timestamp()
        time_since_last_alert = datetime.now().timestamp() - last_alert_time
        return time_since_last_alert >= self.alert_cooldown
