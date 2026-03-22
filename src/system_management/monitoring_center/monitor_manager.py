"""
监控中心 - 监控管理器
统一入口，启动/停止定期采集，获取指标快照，健康判断
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .application_monitor import ApplicationMonitor
from .base_monitor import BaseMonitor
from .metrics_collector import MetricsCollector
from .system_monitor import SystemMonitor


class MonitorManager:
    """
    监控管理器
    - 管理多个监控器
    - 定期后台采集指标
    - 统一获取指标快照
    - 健康状态判断
    单例模式
    """

    _instance: Optional["MonitorManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "MonitorManager":
        """单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化，只执行一次"""
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._monitors: Dict[str, BaseMonitor] = {}
        self._collector = MetricsCollector()
        self._collect_interval: float = 15.0
        self._collect_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # 健康阈值
        self._thresholds: Dict[str, Dict[str, float]] = {
            "cpu_usage_percent": {"warning": 70, "critical": 90},
            "memory_usage_percent": {"warning": 80, "critical": 95},
            "disk_usage_percent": {"warning": 85, "critical": 95},
        }

        # 默认添加系统监控
        self.add_monitor(SystemMonitor())
        # 默认添加应用监控
        self.add_monitor(ApplicationMonitor())

    def initialize(
        self,
        collect_interval_seconds: float = 15.0,
        auto_start: bool = True,
    ) -> None:
        """
        初始化监控管理器

        Args:
            collect_interval_seconds: 采集间隔（秒）
            auto_start: 是否自动启动采集
        """
        self._collect_interval = collect_interval_seconds
        if auto_start:
            self.start()

    def add_monitor(self, monitor: BaseMonitor) -> "MonitorManager":
        """添加监控器"""
        self._monitors[monitor.name] = monitor
        return self

    def get_monitor(self, name: str) -> Optional[BaseMonitor]:
        """获取监控器"""
        return self._monitors.get(name)

    def get_application_monitor(self) -> Optional[ApplicationMonitor]:
        """获取应用监控器"""
        return self.get_monitor("application")  # type: ignore

    def set_threshold(self, metric: str, warning: float, critical: float) -> None:
        """设置指标健康阈值"""
        self._thresholds[metric] = {"warning": warning, "critical": critical}

    def collect_once(self) -> Dict[str, Any]:
        """手动采集一次所有监控器"""
        all_metrics: Dict[str, Any] = {}
        for name, monitor in self._monitors.items():
            metrics = monitor.collect()
            self._collector.record_metrics(metrics)
            all_metrics[name] = metrics
        return all_metrics

    def _collect_loop(self) -> None:
        """后台采集循环"""
        while not self._stop_event.is_set():
            try:
                self.collect_once()
            except Exception:
                pass

            # 等待指定间隔，或者被停止
            self._stop_event.wait(self._collect_interval)

    def start(self) -> None:
        """启动后台采集"""
        if self._running:
            return

        self._stop_event.clear()
        self._collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collect_thread.start()
        self._running = True

    def stop(self) -> None:
        """停止后台采集"""
        if not self._running:
            return

        self._stop_event.set()
        if self._collect_thread is not None:
            self._collect_thread.join(timeout=2.0)
            self._collect_thread = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """获取最新指标快照"""
        return self._collector.get_snapshot()

    def get_metrics_history(self, name: str) -> List[Tuple[float, float]]:
        """获取指标历史"""
        return self._collector.get_history(name)

    def export_prometheus(self) -> str:
        """导出为 Prometheus 格式"""
        return self._collector.to_prometheus()

    def check_health(self) -> Dict[str, Any]:
        """
        检查系统健康状态

        Returns:
            健康检查结果：状态（ok, warning, critical）和各指标详情
        """
        snapshot = self.get_metrics_snapshot()
        if not snapshot:
            # 如果还没有采集数据，先采集一次
            self.collect_once()
            snapshot = self.get_metrics_snapshot()

        result = {
            "status": "ok",
            "metrics": {},
            "issues": [],
        }

        for metric, thresholds in self._thresholds.items():
            if metric not in snapshot:
                continue

            value = snapshot[metric]
            status = "ok"

            if value >= thresholds["critical"]:
                status = "critical"
                result["issues"].append(
                    {
                        "metric": metric,
                        "value": value,
                        "threshold": thresholds["critical"],
                        "level": "critical",
                    }
                )
            elif value >= thresholds["warning"]:
                status = "warning"
                result["issues"].append(
                    {
                        "metric": metric,
                        "value": value,
                        "threshold": thresholds["warning"],
                        "level": "warning",
                    }
                )

            result["metrics"][metric] = {
                "value": value,
                "status": status,
                "warning_threshold": thresholds["warning"],
                "critical_threshold": thresholds["critical"],
            }

        # 确定整体状态
        if any(i["level"] == "critical" for i in result["issues"]):
            result["status"] = "critical"
        elif any(i["level"] == "warning" for i in result["issues"]):
            result["status"] = "warning"
        else:
            result["status"] = "ok"

        return result

    def record_request(
        self,
        latency_seconds: float,
        is_error: bool = False,
    ) -> None:
        """
        快捷记录请求（用于应用监控）

        Args:
            latency_seconds: 请求耗时
            is_error: 是否出错
        """
        app_monitor = self.get_application_monitor()
        if app_monitor:
            app_monitor.record_request(latency_seconds, is_error)

    def shutdown(self) -> None:
        """关闭管理器"""
        self.stop()


# 全局实例
def get_monitor_manager() -> MonitorManager:
    """获取全局监控管理器实例"""
    return MonitorManager()
