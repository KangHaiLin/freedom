"""
数据采集监控服务
负责监控数据采集任务的进度、成功率、速度、异常等情况
"""
from typing import List, Dict, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging

from .base_monitor import BaseMonitor, MonitorResult, AlertLevel
from ..data_ingestion.data_source_manager import data_source_manager
from ..data_storage.storage_manager import storage_manager
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class CollectionMonitor(BaseMonitor):
    """数据采集监控服务"""

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.collection_rules = self.config.get('collection_rules', {
            'success_rate_threshold': 0.95,  # 采集成功率阈值
            'speed_threshold': 1000,  # 采集速度阈值（条/秒）
            'error_rate_threshold': 0.05,  # 错误率阈值
            'task_timeout': 300  # 采集任务超时时间（秒）
        })
        self.clickhouse_storage = storage_manager.get_storage_by_type('clickhouse')
        self.redis_storage = storage_manager.get_storage_by_type('redis')

    def run_check(self) -> MonitorResult:
        """执行采集监控检查"""
        metrics = {}
        issues = []
        overall_success = True
        overall_level = AlertLevel.INFO

        # 1. 数据源状态检查
        source_status_result = self._check_data_source_status()
        metrics['data_sources'] = source_status_result['metrics']
        if not source_status_result['success']:
            issues.append(source_status_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.ERROR)

        # 2. 采集成功率检查
        success_rate_result = self._check_collection_success_rate()
        metrics['success_rate'] = success_rate_result['metrics']
        if not success_rate_result['success']:
            issues.append(success_rate_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.WARNING)

        # 3. 采集速度检查
        speed_result = self._check_collection_speed()
        metrics['collection_speed'] = speed_result['metrics']
        if not speed_result['success']:
            issues.append(speed_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.WARNING)

        # 4. 任务状态检查
        task_status_result = self._check_task_status()
        metrics['tasks'] = task_status_result['metrics']
        if not task_status_result['success']:
            issues.append(task_status_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.ERROR)

        # 构建结果
        if overall_success:
            message = "采集监控检查通过，所有指标正常"
        else:
            message = "采集监控发现问题：" + "; ".join(issues)

        return MonitorResult(
            monitor_name="数据采集监控",
            success=overall_success,
            message=message,
            level=overall_level,
            metrics=metrics
        )

    def _check_data_source_status(self) -> Dict:
        """检查数据源状态"""
        metrics = {}
        success = True
        message = ""

        try:
            source_status = data_source_manager.get_source_status()
            metrics['total_sources'] = len(source_status)
            metrics['available_sources'] = sum(1 for s in source_status if s['is_available'])
            metrics['sources'] = source_status

            unavailable_sources = [s['source'] for s in source_status if not s['is_available']]
            if unavailable_sources:
                success = False
                message = f"以下数据源不可用：{', '.join(unavailable_sources)}"

        except Exception as e:
            logger.error(f"数据源状态检查失败：{e}")
            success = False
            message = f"数据源状态检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_collection_success_rate(self) -> Dict:
        """检查采集成功率"""
        metrics = {}
        success = True
        message = ""

        try:
            # 查询最近1小时的采集结果统计
            end_time = DateTimeUtils.now()
            start_time = end_time - timedelta(hours=1)

            if self.clickhouse_storage:
                df = self.clickhouse_storage.execute_sql(f"""
                    SELECT status, count(*) as cnt
                    FROM collection_log
                    WHERE create_time >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
                    GROUP BY status
                """)

                if not df.empty:
                    total = df['cnt'].sum()
                    success_count = df[df['status'] == 'success']['cnt'].sum() if 'success' in df['status'].values else 0
                    fail_count = df[df['status'] == 'fail']['cnt'].sum() if 'fail' in df['status'].values else 0

                    success_rate = success_count / total if total > 0 else 1.0
                    error_rate = fail_count / total if total > 0 else 0.0

                    metrics['total_requests'] = total
                    metrics['success_count'] = success_count
                    metrics['fail_count'] = fail_count
                    metrics['success_rate'] = success_rate
                    metrics['error_rate'] = error_rate

                    if success_rate < self.collection_rules['success_rate_threshold']:
                        success = False
                        message = f"采集成功率不足：{success_rate:.2%}，阈值：{self.collection_rules['success_rate_threshold']:.2%}"

                    if error_rate > self.collection_rules['error_rate_threshold']:
                        success = False
                        message += f" 采集错误率过高：{error_rate:.2%}，阈值：{self.collection_rules['error_rate_threshold']:.2%}"

        except Exception as e:
            logger.error(f"采集成功率检查失败：{e}")
            success = False
            message = f"采集成功率检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_collection_speed(self) -> Dict:
        """检查采集速度"""
        metrics = {}
        success = True
        message = ""

        try:
            # 查询最近10分钟的采集速度
            if self.redis_storage:
                speed_records = self.redis_storage.read('collection_metrics', {'pattern': 'collection_speed:*'})
                if speed_records:
                    recent_speeds = [float(v) for v in speed_records.values() if v]
                    if recent_speeds:
                        avg_speed = sum(recent_speeds) / len(recent_speeds)
                        max_speed = max(recent_speeds)
                        min_speed = min(recent_speeds)

                        metrics['avg_speed'] = avg_speed
                        metrics['max_speed'] = max_speed
                        metrics['min_speed'] = min_speed

                        if avg_speed < self.collection_rules['speed_threshold']:
                            success = False
                            message = f"采集速度过慢：{avg_speed:.0f}条/秒，阈值：{self.collection_rules['speed_threshold']}条/秒"

        except Exception as e:
            logger.error(f"采集速度检查失败：{e}")
            success = False
            message = f"采集速度检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_task_status(self) -> Dict:
        """检查采集任务状态"""
        metrics = {}
        success = True
        message = ""

        try:
            if self.redis_storage:
                task_records = self.redis_storage.read('collection_tasks', {'pattern': 'task:*'})
                if task_records:
                    running_tasks = []
                    timeout_tasks = []
                    now = DateTimeUtils.now().timestamp()

                    for task_id, task_info in task_records.items():
                        if task_info.get('status') == 'running':
                            start_time = task_info.get('start_time', now)
                            if isinstance(start_time, str):
                                start_time = DateTimeUtils.parse(start_time).timestamp()
                            running_time = now - start_time

                            if running_time > self.collection_rules['task_timeout']:
                                timeout_tasks.append(f"{task_id}（已运行{running_time:.0f}秒）")
                            else:
                                running_tasks.append(task_id)

                    metrics['running_tasks_count'] = len(running_tasks)
                    metrics['timeout_tasks_count'] = len(timeout_tasks)
                    metrics['running_tasks'] = running_tasks
                    metrics['timeout_tasks'] = timeout_tasks

                    if timeout_tasks:
                        success = False
                        message = f"以下采集任务超时：{', '.join(timeout_tasks)}，超时阈值：{self.collection_rules['task_timeout']}秒"

        except Exception as e:
            logger.error(f"任务状态检查失败：{e}")
            success = False
            message = f"任务状态检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }
