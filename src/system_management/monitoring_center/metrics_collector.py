"""
监控中心 - 指标收集器
滑动窗口保留最近数据，支持聚合计算，可导出Prometheus格式
"""
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from .base_monitor import BaseMonitor


class MetricsCollector:
    """
    指标收集器
    - 滑动窗口保留最近指标数据
    - 支持聚合计算（avg, max, min, p95, p99）
    - 支持导出为 Prometheus 格式
    """

    def __init__(
        self,
        max_history_points: int = 1000,
    ):
        """
        初始化指标收集器

        Args:
            max_history_points: 最大保留数据点数
        """
        self.max_history_points = max_history_points
        self._history: Dict[str, deque] = {}
        self._timestamps: deque[float] = deque(maxlen=max_history_points)

    def record(self, name: str, value: float, timestamp: Optional[float] = None) -> None:
        """
        记录一个指标点

        Args:
            name: 指标名
            value: 指标值
            timestamp: 时间戳，默认为当前时间
        """
        if timestamp is None:
            timestamp = time.time()

        if name not in self._history:
            self._history[name] = deque(maxlen=self.max_history_points)

        self._history[name].append((timestamp, value))

        # 只有第一次记录或者有新时间点才添加时间戳
        if not self._timestamps or timestamp != self._timestamps[-1]:
            self._timestamps.append(timestamp)

    def record_metrics(self, metrics: Dict[str, float], timestamp: Optional[float] = None) -> None:
        """批量记录多个指标"""
        if timestamp is None:
            timestamp = time.time()
        for name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.record(name, float(value), timestamp)

    def get_history(self, name: str) -> List[Tuple[float, float]]:
        """获取指标历史"""
        if name not in self._history:
            return []
        return list(self._history[name])

    def get_recent(self, name: str, count: int = 10) -> List[Tuple[float, float]]:
        """获取最近 N 个数据点"""
        history = self.get_history(name)
        return history[-count:]

    def aggregate(
        self,
        name: str,
    ) -> Dict[str, Optional[float]]:
        """
        聚合计算指标

        返回：avg, min, max, p50, p95, p99
        """
        history = self.get_history(name)
        if not history:
            return {
                'avg': None,
                'min': None,
                'max': None,
                'p50': None,
                'p95': None,
                'p99': None,
                'count': 0,
            }

        values = [v for _, v in history]
        sorted_values = sorted(values)
        n = len(sorted_values)

        def percentile(p: float) -> float:
            index = int(n * p / 100.0)
            if index >= n:
                index = n - 1
            return sorted_values[index]

        return {
            'avg': sum(values) / n,
            'min': min(values),
            'max': max(values),
            'p50': percentile(50),
            'p95': percentile(95),
            'p99': percentile(99),
            'count': n,
        }

    def get_snapshot(self) -> Dict[str, float]:
        """获取最新指标快照（每个指标最新一个点）"""
        snapshot: Dict[str, float] = {}
        for name, history in self._history.items():
            if history:
                snapshot[name] = history[-1][1]
        return snapshot

    def to_prometheus(self) -> str:
        """
        导出为 Prometheus 格式

        Returns:
            Prometheus 格式的文本
        """
        lines: List[str] = []
        snapshot = self.get_snapshot()

        for name, value in snapshot.items():
            # 转换名称为 Prometheus 格式
            prom_name = name.replace('.', '_').replace('-', '_')
            lines.append(f"# TYPE {prom_name} gauge")
            lines.append(f"{prom_name} {value}")

        return "\n".join(lines)

    def collect_from_monitor(self, monitor: BaseMonitor) -> None:
        """从监控器收集指标"""
        metrics = monitor.collect()
        self.record_metrics(metrics)

    def cleanup_old(self, keep_seconds: float) -> int:
        """
        清理超过指定时间的旧数据

        Args:
            keep_seconds: 保留最近多少秒的数据

        Returns:
            清理的数据点数
        """
        cutoff = time.time() - keep_seconds
        removed = 0

        for name in list(self._history.keys()):
            history = self._history[name]
            # 移除开头过期的
            while history and history[0][0] < cutoff:
                history.popleft()
                removed += 1

            if not history:
                del self._history[name]

        # 清理时间戳
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        return removed

    def get_all_names(self) -> List[str]:
        """获取所有指标名称"""
        return list(self._history.keys())
