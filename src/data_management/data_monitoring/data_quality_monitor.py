"""
数据质量监控服务
负责监控数据的完整性、准确性、一致性、时效性等质量指标
"""
from typing import List, Dict, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging

from .base_monitor import BaseMonitor, MonitorResult, AlertLevel
from ..data_query.query_manager import query_manager
from ..data_storage.storage_manager import storage_manager
from common.constants import BusinessConstants
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class DataQualityMonitor(BaseMonitor):
    """数据质量监控服务"""

    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.quality_rules = self.config.get('quality_rules', {
            'completeness_threshold': 0.95,  # 数据完整度阈值
            'accuracy_threshold': 0.99,  # 数据准确率阈值
            'timeliness_threshold': 300,  # 数据时效性阈值（秒）
            'consistency_threshold': 0.99  # 数据一致性阈值
        })
        self.clickhouse_storage = storage_manager.get_storage_by_type('clickhouse')
        self.postgresql_storage = storage_manager.get_storage_by_type('postgresql')

    def run_check(self) -> MonitorResult:
        """执行数据质量检查"""
        metrics = {}
        issues = []
        overall_success = True
        overall_level = AlertLevel.INFO

        # 1. 完整性检查
        completeness_result = self._check_completeness()
        metrics['completeness'] = completeness_result['metrics']
        if not completeness_result['success']:
            issues.append(completeness_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.WARNING)

        # 2. 准确性检查
        accuracy_result = self._check_accuracy()
        metrics['accuracy'] = accuracy_result['metrics']
        if not accuracy_result['success']:
            issues.append(accuracy_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.WARNING)

        # 3. 时效性检查
        timeliness_result = self._check_timeliness()
        metrics['timeliness'] = timeliness_result['metrics']
        if not timeliness_result['success']:
            issues.append(timeliness_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.ERROR)

        # 4. 一致性检查
        consistency_result = self._check_consistency()
        metrics['consistency'] = consistency_result['metrics']
        if not consistency_result['success']:
            issues.append(consistency_result['message'])
            overall_success = False
            overall_level = max(overall_level, AlertLevel.ERROR)

        # 计算质量得分
        quality_score = self._calculate_quality_score(metrics)
        metrics['quality_score'] = quality_score

        # 构建结果
        if overall_success:
            message = f"数据质量检查通过，综合得分：{quality_score:.2f}"
        else:
            message = "数据质量检查发现问题：" + "; ".join(issues)

        return MonitorResult(
            monitor_name="数据质量监控",
            success=overall_success,
            message=message,
            level=overall_level,
            metrics=metrics
        )

    def _check_completeness(self) -> Dict:
        """检查数据完整性：是否有缺失数据"""
        metrics = {}
        success = True
        message = ""

        try:
            # 检查最近24小时的行情数据完整性
            end_time = DateTimeUtils.now()
            start_time = end_time - timedelta(hours=24)

            # 查询每日应该有的交易数据量
            expected_count = 4 * 60 * 2500  # 每分钟4条，每天4小时，2500只股票
            actual_count = 0

            # 从ClickHouse查询实际数据量
            if self.clickhouse_storage:
                df = self.clickhouse_storage.execute_sql(f"""
                    SELECT count(*) as cnt
                    FROM market_minute_quote
                    WHERE trade_time >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
                """)
                actual_count = df.iloc[0]['cnt'] if not df.empty else 0

            completeness_rate = min(1.0, actual_count / expected_count) if expected_count > 0 else 0
            metrics['completeness_rate'] = completeness_rate
            metrics['expected_count'] = expected_count
            metrics['actual_count'] = actual_count

            if completeness_rate < self.quality_rules['completeness_threshold']:
                success = False
                message = f"数据完整度不足：{completeness_rate:.2%}，阈值：{self.quality_rules['completeness_threshold']:.2%}"

        except Exception as e:
            logger.error(f"完整性检查失败：{e}")
            success = False
            message = f"完整性检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_accuracy(self) -> Dict:
        """检查数据准确性：价格等字段是否合理"""
        metrics = {}
        success = True
        message = ""

        try:
            # 检查价格是否在合理范围内
            if self.clickhouse_storage:
                df = self.clickhouse_storage.execute_sql("""
                    SELECT count(*) as total,
                           sum(CASE WHEN close <= 0 OR close > 10000 THEN 1 ELSE 0 END) as invalid_price,
                           sum(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as invalid_volume
                    FROM market_daily_quote
                    WHERE trade_date >= today() - 7
                """)

                if not df.empty:
                    total = df.iloc[0]['total']
                    invalid_price = df.iloc[0]['invalid_price']
                    invalid_volume = df.iloc[0]['invalid_volume']

                    accuracy_rate = (total - invalid_price - invalid_volume) / total if total > 0 else 0
                    metrics['accuracy_rate'] = accuracy_rate
                    metrics['total_records'] = total
                    metrics['invalid_price_count'] = invalid_price
                    metrics['invalid_volume_count'] = invalid_volume

                    if accuracy_rate < self.quality_rules['accuracy_threshold']:
                        success = False
                        message = f"数据准确率不足：{accuracy_rate:.2%}，阈值：{self.quality_rules['accuracy_threshold']:.2%}"

        except Exception as e:
            logger.error(f"准确性检查失败：{e}")
            success = False
            message = f"准确性检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_timeliness(self) -> Dict:
        """检查数据时效性：最新数据是否及时更新"""
        metrics = {}
        success = True
        message = ""

        try:
            # 检查实时行情最新数据时间
            if self.postgresql_storage:
                df = self.postgresql_storage.execute_sql("""
                    SELECT max(time) as latest_time
                    FROM market_realtime_quote
                """)

                if not df.empty and df.iloc[0]['latest_time']:
                    latest_time = pd.to_datetime(df.iloc[0]['latest_time'])
                    delay = (DateTimeUtils.now() - latest_time).total_seconds()
                    metrics['latest_data_time'] = DateTimeUtils.to_str(latest_time)
                    metrics['delay_seconds'] = delay

                    if delay > self.quality_rules['timeliness_threshold']:
                        success = False
                        message = f"数据延迟过大：{delay:.0f}秒，阈值：{self.quality_rules['timeliness_threshold']}秒"

        except Exception as e:
            logger.error(f"时效性检查失败：{e}")
            success = False
            message = f"时效性检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _check_consistency(self) -> Dict:
        """检查数据一致性：不同来源数据是否一致"""
        metrics = {}
        success = True
        message = ""

        try:
            # 检查日线和分钟线的收盘价是否一致
            if self.clickhouse_storage:
                df = self.clickhouse_storage.execute_sql("""
                    SELECT d.stock_code, d.trade_date, d.close as daily_close, m.close as minute_close
                    FROM market_daily_quote d
                    JOIN (
                        SELECT stock_code, toDate(trade_time) as trade_date,
                               argMax(close, trade_time) as close
                        FROM market_minute_quote
                        WHERE trade_time >= today() - 1
                        GROUP BY stock_code, toDate(trade_time)
                    ) m ON d.stock_code = m.stock_code AND d.trade_date = m.trade_date
                    WHERE d.trade_date >= today() - 1
                """)

                if not df.empty:
                    total = len(df)
                    inconsistent = len(df[abs(df['daily_close'] - df['minute_close']) > 0.01])
                    consistency_rate = (total - inconsistent) / total if total > 0 else 0
                    metrics['consistency_rate'] = consistency_rate
                    metrics['total_compared'] = total
                    metrics['inconsistent_count'] = inconsistent

                    if consistency_rate < self.quality_rules['consistency_threshold']:
                        success = False
                        message = f"数据一致性不足：{consistency_rate:.2%}，阈值：{self.quality_rules['consistency_threshold']:.2%}"

        except Exception as e:
            logger.error(f"一致性检查失败：{e}")
            success = False
            message = f"一致性检查异常：{str(e)}"
            metrics['error'] = str(e)

        return {
            'success': success,
            'message': message,
            'metrics': metrics
        }

    def _calculate_quality_score(self, metrics: Dict) -> float:
        """计算综合数据质量得分"""
        weights = {
            'completeness': 0.25,
            'accuracy': 0.3,
            'timeliness': 0.25,
            'consistency': 0.2
        }

        score = 0.0
        for key, weight in weights.items():
            if key in metrics and f'{key}_rate' in metrics[key]:
                score += metrics[key][f'{key}_rate'] * weight

        return round(score * 100, 2)
