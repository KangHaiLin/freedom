"""
监控管理器
统一管理所有监控任务，负责任务调度、执行、告警发送和结果存储
"""
from typing import List, Dict, Optional, Any
import threading
import time
from datetime import datetime, timedelta
import logging
import json

from .base_monitor import BaseMonitor, MonitorResult
from .data_quality_monitor import DataQualityMonitor
from .collection_monitor import CollectionMonitor
from .alert_service import alert_service
from ..data_storage.storage_manager import storage_manager
from common.config import settings
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class MonitorManager:
    """监控管理器"""

    def __init__(self):
        self.monitors: List[BaseMonitor] = []
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.alert_service = alert_service
        self.storage = storage_manager.get_storage_by_type('clickhouse')
        self.redis_storage = storage_manager.get_storage_by_type('redis')
        self.config = settings.MONITOR_CONFIG
        self._init_monitors()

    def _init_monitors(self):
        """初始化所有监控实例"""
        try:
            # 数据质量监控
            if self.config.get('enable_data_quality_monitor', True):
                self.monitors.append(DataQualityMonitor(self.config.get('data_quality', {})))
                logger.info("数据质量监控已加载")

            # 采集监控
            if self.config.get('enable_collection_monitor', True):
                self.monitors.append(CollectionMonitor(self.config.get('collection', {})))
                logger.info("采集监控已加载")

            logger.info(f"共加载{len(self.monitors)}个监控任务")

        except Exception as e:
            logger.error(f"初始化监控失败：{e}")
            raise

    def add_monitor(self, monitor: BaseMonitor):
        """添加监控任务"""
        self.monitors.append(monitor)
        logger.info(f"添加监控任务：{monitor.__class__.__name__}")

    def remove_monitor(self, monitor_class):
        """移除监控任务"""
        self.monitors = [m for m in self.monitors if not isinstance(m, monitor_class)]
        logger.info(f"移除监控任务：{monitor_class.__name__}")

    def run_all_once(self) -> List[MonitorResult]:
        """立即执行所有监控一次"""
        results = []
        logger.info("开始执行所有监控检查")

        for monitor in self.monitors:
            try:
                result = monitor.run()
                if result:
                    results.append(result)
                    # 发送告警
                    self.alert_service.send_alert(result)
                    # 存储结果
                    self._save_monitor_result(result)
            except Exception as e:
                logger.error(f"执行监控{monitor.__class__.__name__}失败：{e}")

        logger.info(f"所有监控检查完成，共产生{len(results)}条告警")
        return results

    def _scheduler_loop(self):
        """调度循环"""
        logger.info("监控调度器已启动")
        while self.running:
            try:
                current_time = time.time()
                for monitor in self.monitors:
                    # 检查是否到了执行时间
                    if not monitor.last_run_time or \
                       (current_time - monitor.last_run_time.timestamp()) >= monitor.interval:
                        try:
                            result = monitor.run()
                            if result:
                                # 发送告警
                                self.alert_service.send_alert(result)
                                # 存储结果
                                self._save_monitor_result(result)
                        except Exception as e:
                            logger.error(f"执行监控{monitor.__class__.__name__}失败：{e}")

                # 休眠1秒
                time.sleep(1)

            except Exception as e:
                logger.error(f"监控调度循环异常：{e}")
                time.sleep(5)

        logger.info("监控调度器已停止")

    def start(self):
        """启动监控调度器"""
        if self.running:
            logger.warning("监控调度器已经在运行中")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("监控调度器启动成功")

    def stop(self):
        """停止监控调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("监控调度器已停止")

    def _save_monitor_result(self, result: MonitorResult):
        """保存监控结果到数据库"""
        try:
            if not self.storage:
                return

            data = [{
                "monitor_name": result.monitor_name,
                "success": result.success,
                "message": result.message,
                "level": result.level.value,
                "metrics": json.dumps(result.metrics, ensure_ascii=False),
                "details": json.dumps(result.details, ensure_ascii=False),
                "timestamp": result.timestamp
            }]

            self.storage.write("monitor_results", data)
            logger.debug(f"监控结果已保存：{result.monitor_name}")

        except Exception as e:
            logger.error(f"保存监控结果失败：{e}")

    def get_monitor_status(self) -> List[Dict]:
        """获取所有监控的状态"""
        return [monitor.get_status() for monitor in self.monitors]

    def get_recent_alerts(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """查询历史告警记录"""
        try:
            if not self.storage:
                return []

            conditions = []
            params = []

            if level:
                conditions.append("level = %s")
                params.append(level)
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT * FROM monitor_results
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT {limit}
            """

            df = self.storage.execute_sql(sql, params=params)
            return df.to_dict('records') if not df.empty else []

        except Exception as e:
            logger.error(f"查询历史告警失败：{e}")
            return []

    def get_dashboard_data(self) -> Dict:
        """获取监控面板数据"""
        data = {
            "monitor_count": len(self.monitors),
            "running": self.running,
            "monitor_status": self.get_monitor_status(),
            "recent_alerts": self.get_recent_alerts(limit=20),
            "24h_alert_count": 0,
            "error_count": 0,
            "warning_count": 0
        }

        try:
            # 统计24小时告警
            if self.storage:
                df = self.storage.execute_sql("""
                    SELECT level, count(*) as cnt
                    FROM monitor_results
                    WHERE timestamp >= now() - INTERVAL 24 HOUR
                    GROUP BY level
                """)

                if not df.empty:
                    for _, row in df.iterrows():
                        cnt = row['cnt']
                        data['24h_alert_count'] += cnt
                        if row['level'] == 'error':
                            data['error_count'] = cnt
                        elif row['level'] == 'warning':
                            data['warning_count'] = cnt

        except Exception as e:
            logger.error(f"获取监控面板数据失败：{e}")

        return data

    def health_check(self) -> Dict:
        """监控服务健康检查"""
        return {
            "status": "healthy" if self.running else "stopped",
            "monitor_count": len(self.monitors),
            "running": self.running,
            "alert_service_healthy": True,
            "check_time": DateTimeUtils.now_str()
        }


# 全局监控管理器实例
monitor_manager = MonitorManager()
