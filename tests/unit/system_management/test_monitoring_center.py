"""
测试监控中心
"""
import time
from src.system_management.monitoring_center import (
    BaseMonitor,
    SystemMonitor,
    ApplicationMonitor,
    MetricsCollector,
    MonitorManager,
)


def test_system_monitor():
    """测试系统资源监控"""
    monitor = SystemMonitor()
    metrics = monitor.collect()

    assert 'cpu_usage_percent' in metrics
    assert 'memory_usage_percent' in metrics
    assert 'memory_total_bytes' in metrics
    assert 0 <= metrics['cpu_usage_percent'] <= 100
    assert 0 <= metrics['memory_usage_percent'] <= 100

    # 再次获取
    again = monitor.get_metrics()
    assert 'cpu_usage_percent' in again


def test_application_monitor():
    """测试应用性能监控"""
    monitor = ApplicationMonitor()

    # 记录一些请求
    monitor.record_request(0.1, False)
    monitor.record_request(0.2, False)
    monitor.record_request(0.5, True)
    monitor.record_request(0.05, False)

    metrics = monitor.collect()

    assert 'qps' in metrics
    assert 'error_rate' in metrics
    assert 'latency_avg_ms' in metrics
    assert 'latency_p95_ms' in metrics
    assert 'latency_p99_ms' in metrics
    assert metrics['total_requests'] == 4
    assert metrics['total_errors'] == 1
    assert metrics['error_rate'] == 25.0  # 1/4 * 100

    # 自定义指标
    monitor.increment('requests', 10)
    monitor.gauge('connections', 5)
    metrics = monitor.collect()
    assert metrics['counter_requests'] == 10
    assert metrics['gauge_connections'] == 5


def test_metrics_collector():
    """测试指标收集器"""
    collector = MetricsCollector(max_history_points=100)

    # 记录一些指标
    base_time = time.time()
    for i in range(10):
        collector.record('test_metric', i * 10, base_time + i)

    assert len(collector.get_history('test_metric')) == 10

    # 聚合
    agg = collector.aggregate('test_metric')
    assert agg['min'] == 0
    assert agg['max'] == 90
    assert agg['avg'] == 45
    assert agg['count'] == 10

    # 快照
    snapshot = collector.get_snapshot()
    assert snapshot['test_metric'] == 90

    # Prometheus 导出
    prom = collector.to_prometheus()
    assert 'test_metric' in prom


def test_metrics_collector_cleanup():
    """测试清理旧数据"""
    collector = MetricsCollector()
    base_time = time.time()

    # 旧数据
    collector.record('old', 1, base_time - 3600)  # 1 小时前
    collector.record('new', 2, base_time)

    removed = collector.cleanup_old(keep_seconds=1800)  # 保留 30 分钟
    assert removed == 1
    assert len(collector.get_history('old')) == 0
    assert len(collector.get_history('new')) == 1


def test_monitor_manager():
    """测试监控管理器"""
    manager = MonitorManager()
    # 重新初始化
    manager._initialized = True

    manager.initialize(collect_interval_seconds=1, auto_start=False)

    # 初始收集
    metrics = manager.collect_once()
    assert 'system' in metrics
    assert 'application' in metrics

    snapshot = manager.get_metrics_snapshot()
    assert 'cpu_usage_percent' in snapshot

    # 健康检查
    health = manager.check_health()
    assert 'status' in health
    assert 'issues' in health
    assert 'metrics' in health

    # 快捷记录请求
    manager.record_request(0.1)

    manager.shutdown()
    assert not manager.is_running


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
