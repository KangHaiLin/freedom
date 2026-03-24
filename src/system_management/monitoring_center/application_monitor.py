"""
监控中心 - 应用性能监控
统计请求计数、QPS、延迟分布、错误率等应用指标
"""

import time
from collections import deque
from typing import Dict, List

from .base_monitor import BaseMonitor


class ApplicationMonitor(BaseMonitor):
    """
    应用性能监控器
    统计：
    - 请求计数和 QPS
    - 请求延迟分布（平均、p50、p95、p99）
    - 错误率
    - 自定义指标支持
    """

    def __init__(
        self,
        max_history_seconds: int = 300,  # 保留 5 分钟历史
        bucket_seconds: int = 10,  # 每 10 秒一个桶
    ):
        """
        初始化应用性能监控

        Args:
            max_history_seconds: 最大保留历史秒数
            bucket_seconds: 每个时间桶的秒数
        """
        self.max_history_seconds = max_history_seconds
        self.bucket_seconds = bucket_seconds
        self._num_buckets = max_history_seconds // bucket_seconds

        # 请求统计
        self._request_count: int = 0
        self._error_count: int = 0
        self._latencies: deque = deque(maxlen=self._num_buckets)

        # 每个桶的统计
        self._buckets: List[Dict[str, Any]] = []
        self._last_bucket_time: float = 0.0
        self._custom_metrics: Dict[str, Any] = {}

        self._last_metrics: Dict[str, Any] = {}
        self._start_time = time.time()

        # 初始化第一个桶
        self._create_new_bucket()

    def _create_new_bucket(self) -> None:
        """创建新的时间桶"""
        now = time.time()
        self._buckets.append(
            {
                "start_time": now,
                "request_count": 0,
                "error_count": 0,
                "latencies": [],
            }
        )
        self._last_bucket_time = now

        # 如果超过最大桶数，移除最早的桶
        while len(self._buckets) > self._num_buckets:
            self._buckets.pop(0)

    def _get_current_bucket(self) -> Dict[str, Any]:
        """获取当前时间桶"""
        now = time.time()
        if now - self._last_bucket_time >= self.bucket_seconds:
            self._create_new_bucket()
        return self._buckets[-1]

    def record_request(self, latency_seconds: float, is_error: bool = False) -> None:
        """
        记录请求

        Args:
            latency_seconds: 请求耗时（秒）
            is_error: 是否出错
        """
        bucket = self._get_current_bucket()
        bucket["request_count"] += 1
        bucket["latencies"].append(latency_seconds)
        self._request_count += 1

        if is_error:
            bucket["error_count"] += 1
            self._error_count += 1

    def increment(self, metric_name: str, value: float = 1.0) -> None:
        """
        增加自定义计数器指标

        Args:
            metric_name: 指标名
            value: 增加值
        """
        key = f"counter_{metric_name}"
        if key not in self._custom_metrics:
            self._custom_metrics[key] = 0.0
        self._custom_metrics[key] += value

    def gauge(self, metric_name: str, value: float) -> None:
        """
        设置仪表盘指标（当前值）

        Args:
            metric_name: 指标名
            value: 当前值
        """
        key = f"gauge_{metric_name}"
        self._custom_metrics[key] = value

    def _calculate_percentile(self, latencies: List[float], percentile: float) -> float:
        """计算百分位延迟"""
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        index = int(len(sorted_latencies) * percentile / 100.0)
        if index >= len(sorted_latencies):
            index = len(sorted_latencies) - 1
        return sorted_latencies[index]

    def collect(self) -> Dict[str, Any]:
        """收集应用性能指标"""
        # 聚合所有桶的数据
        total_requests = sum(b["request_count"] for b in self._buckets)
        total_errors = sum(b["error_count"] for b in self._buckets)
        all_latencies = []
        for b in self._buckets:
            all_latencies.extend(b["latencies"])

        # 计算时间窗口
        if len(self._buckets) >= 2:
            time_window = self._buckets[-1]["start_time"] - self._buckets[0]["start_time"]
        else:
            time_window = self.bucket_seconds

        # 计算指标
        metrics: Dict[str, Any] = {}

        # QPS
        if time_window > 0:
            metrics["qps"] = total_requests / time_window
        else:
            metrics["qps"] = total_requests

        # 错误率
        if total_requests > 0:
            metrics["error_rate"] = total_errors / total_requests * 100
        else:
            metrics["error_rate"] = 0.0

        # 延迟统计
        if all_latencies:
            metrics["latency_avg_ms"] = sum(all_latencies) / len(all_latencies) * 1000
            metrics["latency_min_ms"] = min(all_latencies) * 1000
            metrics["latency_max_ms"] = max(all_latencies) * 1000
            metrics["latency_p50_ms"] = self._calculate_percentile(all_latencies, 50) * 1000
            metrics["latency_p95_ms"] = self._calculate_percentile(all_latencies, 95) * 1000
            metrics["latency_p99_ms"] = self._calculate_percentile(all_latencies, 99) * 1000
        else:
            metrics["latency_avg_ms"] = 0
            metrics["latency_p95_ms"] = 0
            metrics["latency_p99_ms"] = 0

        # 累计统计
        metrics["total_requests"] = self._request_count
        metrics["total_errors"] = self._error_count
        metrics["uptime_seconds"] = time.time() - self._start_time

        # 自定义指标
        metrics.update(self._custom_metrics)

        self._last_metrics = metrics
        return metrics

    def get_metrics(self) -> Dict[str, Any]:
        """获取最近收集的指标"""
        return self._last_metrics.copy()

    def reset(self) -> None:
        """重置所有统计"""
        self._buckets.clear()
        self._request_count = 0
        self._error_count = 0
        self._custom_metrics.clear()
        self._last_metrics.clear()
        self._start_time = time.time()
        self._create_new_bucket()

    @property
    def name(self) -> str:
        return "application"
