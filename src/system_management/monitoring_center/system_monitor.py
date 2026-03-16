"""
监控中心 - 系统资源监控
采集 CPU、内存、磁盘、网络 IO 等系统资源指标
"""
from typing import Any, Dict
import psutil
from .base_monitor import BaseMonitor


class SystemMonitor(BaseMonitor):
    """
    系统资源监控器
    采集 CPU 使用率、内存使用率、磁盘使用率、网络 IO 等指标
    """

    def __init__(self):
        """初始化"""
        self._last_metrics: Dict[str, Any] = {}
        self._last_net_io = psutil.net_io_counters()
        self._last_disk_io = psutil.disk_io_counters()

    def collect_cpu(self) -> Dict[str, float]:
        """收集 CPU 指标"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        metrics = {
            'cpu_usage_percent': cpu_percent,
            'cpu_count': cpu_count,
        }

        if cpu_freq:
            metrics['cpu_freq_current_mhz'] = cpu_freq.current

        per_cpu_percent = psutil.cpu_percent(percpu=True)
        for i, percent in enumerate(per_cpu_percent):
            metrics[f'cpu_{i}_usage_percent'] = percent

        return metrics

    def collect_memory(self) -> Dict[str, float | int]:
        """收集内存指标"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            'memory_total_bytes': mem.total,
            'memory_used_bytes': mem.used,
            'memory_available_bytes': mem.available,
            'memory_usage_percent': mem.percent,
            'swap_total_bytes': swap.total,
            'swap_used_bytes': swap.used,
            'swap_usage_percent': swap.percent,
        }

    def collect_disk(self) -> Dict[str, float | int]:
        """收集磁盘使用率指标"""
        metrics = {}

        # 磁盘使用率
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                mount_name = part.mountpoint.replace('/', '_').strip('_')
                if not mount_name:
                    mount_name = 'root'
                metrics[f'disk_{mount_name}_total_bytes'] = usage.total
                metrics[f'disk_{mount_name}_used_bytes'] = usage.used
                metrics[f'disk_{mount_name}_free_bytes'] = usage.free
                metrics[f'disk_{mount_name}_usage_percent'] = usage.percent
            except PermissionError:
                continue

        # 磁盘 IO
        current_disk_io = psutil.disk_io_counters()
        if self._last_disk_io and current_disk_io:
            read_bytes = current_disk_io.read_bytes - self._last_disk_io.read_bytes
            write_bytes = current_disk_io.write_bytes - self._last_disk_io.write_bytes
            read_count = current_disk_io.read_count - self._last_disk_io.read_count
            write_count = current_disk_io.write_count - self._last_disk_io.write_count
            metrics['disk_read_bytes_per_sec'] = read_bytes
            metrics['disk_write_bytes_per_sec'] = write_bytes
            metrics['disk_read_count_per_sec'] = read_count
            metrics['disk_write_count_per_sec'] = write_count
            self._last_disk_io = current_disk_io

        return metrics

    def collect_network(self) -> Dict[str, float | int]:
        """收集网络 IO 指标"""
        metrics = {}
        current_net_io = psutil.net_io_counters()

        if self._last_net_io:
            bytes_sent = current_net_io.bytes_sent - self._last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self._last_net_io.bytes_recv
            packets_sent = current_net_io.packets_sent - self._last_net_io.packets_sent
            packets_recv = current_net_io.packets_recv - self._last_net_io.packets_recv

            metrics['network_bytes_sent_per_sec'] = bytes_sent
            metrics['network_bytes_recv_per_sec'] = bytes_recv
            metrics['network_packets_sent_per_sec'] = packets_sent
            metrics['network_packets_recv_per_sec'] = packets_recv

        self._last_net_io = current_net_io
        return metrics

    def collect_load_avg(self) -> Dict[str, float]:
        """收集系统负载信息"""
        try:
            load1, load5, load15 = psutil.getloadavg()
            return {
                'load_avg_1min': load1,
                'load_avg_5min': load5,
                'load_avg_15min': load15,
            }
        except Exception:
            return {}

    def collect(self) -> Dict[str, Any]:
        """收集所有系统指标"""
        metrics = {}
        metrics.update(self.collect_cpu())
        metrics.update(self.collect_memory())
        metrics.update(self.collect_disk())
        metrics.update(self.collect_network())
        metrics.update(self.collect_load_avg())
        self._last_metrics = metrics
        return metrics

    def get_metrics(self) -> Dict[str, Any]:
        """获取最近收集的指标"""
        return self._last_metrics.copy()

    @property
    def name(self) -> str:
        return "system"
