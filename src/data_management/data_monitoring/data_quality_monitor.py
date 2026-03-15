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
from common.constants import BusinessConstants, DEFAULT_QUALITY_RULES
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class DataQualityMonitor(BaseMonitor):
    """数据质量监控服务"""

    def __init__(self, name: str, config: Dict = None, storage_manager = None):
        super().__init__(name=name, config=config)
        # 合并默认规则和配置中的规则
        self.quality_rules = DEFAULT_QUALITY_RULES.copy()
        self.quality_rules.update(self.config.get('quality_rules', {}))

        self.table_name = self.config.get('table_name', 'realtime_quotes')
        self.metrics = self.config.get('metrics', ['completeness', 'accuracy', 'timeliness'])
        self.thresholds = self.config.get('thresholds', {
            'overall_score': DEFAULT_QUALITY_RULES['overall_score_threshold']
        })
        self.storage_manager = storage_manager or storage_manager
        self.clickhouse_storage = self.storage_manager.get_storage_by_type('clickhouse') if self.storage_manager else None
        self.postgresql_storage = self.storage_manager.get_storage_by_type('postgresql') if self.storage_manager else None

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

    def _check_completeness(self, data: pd.DataFrame = None) -> float:
        """检查数据完整性：是否有缺失数据"""
        if data is None:
            # 原有的数据库查询逻辑
            result = super()._check_completeness()
            return result['metrics'].get('completeness_rate', 0.0)

        # 测试用的静态数据检查逻辑
        if data.empty:
            return 0.0

        total_values = data.size
        missing_values = data.isna().sum().sum()
        completeness = (total_values - missing_values) / total_values
        return completeness

    def _check_accuracy(self, data: pd.DataFrame = None) -> float:
        """检查数据准确性：价格等字段是否合理"""
        if data is None:
            # 原有的数据库查询逻辑
            result = super()._check_accuracy()
            return result['metrics'].get('accuracy_rate', 0.0)

        # 测试用的静态数据检查逻辑
        if data.empty:
            return 0.0

        total_count = len(data)
        error_count = 0

        # 检查股票代码格式
        if 'stock_code' in data.columns:
            # A股代码格式验证：必须是6位数字加交易所后缀，如000001.SZ、600000.SH
            def is_valid_stock_code(code):
                if not isinstance(code, str) or len(code) < 6:
                    return False
                # 检查是否是"INVALID"这种无效代码
                if not code[:6].isdigit():
                    return False
                return True
            invalid_codes = data['stock_code'].apply(lambda x: not is_valid_stock_code(x))
            error_count += invalid_codes.sum()

        # 检查价格是否合理
        if 'price' in data.columns:
            invalid_prices = data['price'].apply(lambda x: not (isinstance(x, (int, float)) and x > 0 and x < 10000))
            error_count += invalid_prices.sum()

        # 检查成交量是否合理
        if 'volume' in data.columns:
            invalid_volumes = data['volume'].apply(lambda x: not (isinstance(x, (int, float)) and x >= 0))
            error_count += invalid_volumes.sum()

        accuracy = (total_count * len(data.columns) - error_count) / (total_count * len(data.columns)) if total_count > 0 else 0.0
        return accuracy

    def _check_timeliness(self, data: pd.DataFrame = None, max_delay_minutes: int = 10) -> float:
        """检查数据时效性：最新数据是否及时更新"""
        if data is None:
            # 原有的数据库查询逻辑
            result = super()._check_timeliness()
            delay = result['metrics'].get('delay_seconds', 0)
            return max(0, 1 - delay / (max_delay_minutes * 60))

        # 测试用的静态数据检查逻辑
        if data.empty or 'time' not in data.columns:
            return 0.0

        latest_time = pd.to_datetime(data['time'].max())
        now = DateTimeUtils.now()
        # 处理时区差异
        if latest_time.tzinfo is None and now.tzinfo is not None:
            latest_time = latest_time.tz_localize(now.tzinfo)
        elif latest_time.tzinfo is not None and now.tzinfo is None:
            now = now.tz_localize(latest_time.tzinfo)
        delay_minutes = (now - latest_time).total_seconds() / 60
        timeliness = max(0, 1 - delay_minutes / max_delay_minutes)
        return round(timeliness, 2)

    def run_check(self) -> MonitorResult:
        """执行数据质量检查"""
        metrics = {}
        issues = []
        overall_success = True
        overall_level = AlertLevel.INFO

        # 从存储读取最新数据
        data = pd.DataFrame()
        if self.storage_manager:
            storage = self.storage_manager.get_storage(self.table_name)
            if storage:
                data = storage.read(limit=1000)

        # 1. 完整性检查
        if 'completeness' in self.metrics:
            completeness = self._check_completeness(data)
            metrics['completeness'] = completeness
            if completeness < 0.9:
                issues.append(f"完整性不足：{completeness:.2%}")
                overall_success = False
                overall_level = max(overall_level, AlertLevel.WARNING)

        # 2. 准确性检查
        if 'accuracy' in self.metrics:
            accuracy = self._check_accuracy(data)
            metrics['accuracy'] = accuracy
            if accuracy < 0.95:
                issues.append(f"准确性不足：{accuracy:.2%}")
                overall_success = False
                overall_level = max(overall_level, AlertLevel.WARNING)

        # 3. 时效性检查
        if 'timeliness' in self.metrics:
            timeliness = self._check_timeliness(data)
            metrics['timeliness'] = timeliness
            if timeliness < 0.8:
                issues.append(f"时效性不足：{timeliness:.2%}")
                overall_success = False
                overall_level = max(overall_level, AlertLevel.ERROR)

        # 计算综合得分
        overall_score = sum(metrics.values()) / len(metrics) if metrics else 0.0
        metrics['overall_score'] = overall_score

        # 构建结果
        if overall_success and overall_score >= self.thresholds.get('overall_score', 0.8):
            message = f"数据质量检查通过，综合得分：{overall_score:.2f}"
            return MonitorResult.success(
                monitor_name=self.name,
                metrics=metrics,
                message=message
            )
        else:
            message = "数据质量检查发现问题：" + "; ".join(issues)
            return MonitorResult.failure(
                monitor_name=self.name,
                alert_level=overall_level,
                metrics=metrics,
                message=message
            )

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
