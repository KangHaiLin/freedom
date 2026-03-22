"""
告警生成器
根据风险级别生成不同渠道的告警
"""

import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.risk_management.rule_engine.rule_result import RuleViolation

logger = logging.getLogger(__name__)


class AlertLevel:
    """告警级别常量"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """告警对象"""

    def __init__(
        self,
        alert_id: str,
        level: str,
        message: str,
        risk_type: str,
        data: Optional[Dict[str, Any]] = None,
        violation: Optional[RuleViolation] = None,
    ):
        self.alert_id = alert_id
        self.level = level
        self.message = message
        self.risk_type = risk_type
        self.data = data or {}
        self.violation = violation
        self.created_at = datetime.now()
        self.sent = False
        self.sent_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "alert_id": self.alert_id,
            "level": self.level,
            "message": self.message,
            "risk_type": self.risk_type,
            "data": self.data,
            "violation": self.violation.to_dict() if self.violation else None,
            "created_at": self.created_at.isoformat(),
            "sent": self.sent,
            "sent_time": self.sent_time.isoformat() if self.sent_time else None,
        }


# 类型别名
AlertHandler = Callable[[Alert], None]


class AlertGenerator:
    """
    告警生成器
    支持多渠道告警，告警去重，告警抑制
    """

    def __init__(
        self,
        dedup_interval_minutes: int = 5,
        max_cache_size: int = 1000,
    ):
        """
        初始化告警生成器

        Args:
            dedup_interval_minutes: 相同告警去重间隔（分钟）
            max_cache_size: 最大缓存告警数量
        """
        self._dedup_interval = timedelta(minutes=dedup_interval_minutes)
        self._max_cache_size = max_cache_size
        # 告警缓存: event_key -> last_alert_time
        self._alert_cache: OrderedDict[str, datetime] = OrderedDict()
        # 告警处理器注册
        self._handlers: Dict[str, AlertHandler] = {}
        # 存储所有告警
        self._alerts: List[Alert] = []

    def register_handler(self, level: str, handler: AlertHandler) -> None:
        """
        注册指定级别的告警处理器

        Args:
            level: 告警级别
            handler: 处理函数
        """
        self._handlers[level] = handler

    def generate(
        self,
        level: str,
        message: str,
        data: Dict[str, Any],
        violation: Optional[RuleViolation] = None,
        risk_type: str = "unknown",
    ) -> Optional[Alert]:
        """
        生成告警

        Args:
            level: 告警级别
            message: 告警消息
            data: 告警数据
            violation: 规则违规对象
            risk_type: 风险类型

        Returns:
            如果未被去重抑制，返回告警对象；否则返回None
        """
        # 生成去重key
        event_key = f"{risk_type}_{level}_{hash(frozenset(data.items()))}"

        # 检查去重
        if self._should_suppress(event_key):
            logger.debug(f"Alert suppressed by deduplication: {event_key}")
            return None

        # 创建告警对象
        alert_id = f"{int(datetime.now().timestamp())}_{abs(hash(message)) % 10000:04d}"
        alert = Alert(
            alert_id=alert_id,
            level=level,
            message=message,
            risk_type=risk_type,
            data=data,
            violation=violation,
        )

        # 更新缓存
        self._update_cache(event_key)

        # 保存到列表
        self._alerts.append(alert)
        if len(self._alerts) > self._max_cache_size:
            self._alerts = self._alerts[-self._max_cache_size :]

        # 分发告警
        self._dispatch(alert)

        return alert

    def _should_suppress(self, event_key: str) -> bool:
        """检查是否应该抑制此告警"""
        if event_key not in self._alert_cache:
            return False
        last_time = self._alert_cache[event_key]
        now = datetime.now()
        if (now - last_time) < self._dedup_interval:
            return True
        return False

    def _update_cache(self, event_key: str) -> None:
        """更新告警缓存"""
        self._alert_cache[event_key] = datetime.now()
        # LRU淘汰
        if len(self._alert_cache) > self._max_cache_size:
            self._alert_cache.popitem(last=False)

    def _dispatch(self, alert: Alert) -> None:
        """分发告警到处理器"""
        # 先处理特定级别
        if alert.level in self._handlers:
            try:
                self._handlers[alert.level](alert)
                alert.sent = True
                alert.sent_time = datetime.now()
            except Exception as e:
                logger.error(f"Error handling alert: {e}")
        else:
            # 默认使用日志
            self._default_log_handler(alert)
            alert.sent = True
            alert.sent_time = datetime.now()

    def _default_log_handler(self, alert: Alert) -> None:
        """默认日志处理器"""
        log_msg = f"ALERT [{alert.level}] {alert.risk_type}: {alert.message}"
        if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
            logger.error(log_msg)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def get_recent_alerts(self, count: int = 100) -> List[Alert]:
        """获取最近的告警"""
        return self._alerts[-count:]

    def get_alerts_by_level(self, level: str) -> List[Alert]:
        """按级别获取告警"""
        return [a for a in self._alerts if a.level == level]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._alert_cache.clear()

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "total_alerts": len(self._alerts),
            "cached_alerts": len(self._alert_cache),
        }
