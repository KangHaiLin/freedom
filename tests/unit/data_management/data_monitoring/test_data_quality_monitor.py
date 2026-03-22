"""
Unit tests for data_quality_monitor.py
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pandas as pd
import pytest

from common.constants import DEFAULT_QUALITY_RULES
from data_management.data_monitoring.base_monitor import AlertLevel, MonitorResult
from data_management.data_monitoring.data_quality_monitor import DataQualityMonitor


class TestDataQualityMonitor:
    """测试数据质量监控"""

    def test_init_default(self):
        """测试默认初始化"""
        monitor = DataQualityMonitor(name="quality_check")
        assert monitor.name == "quality_check"
        assert monitor.quality_rules == DEFAULT_QUALITY_RULES
        assert "completeness_threshold" in monitor.quality_rules
        assert "accuracy_threshold" in monitor.quality_rules
        # 小数会转为百分比
        expected_overall = DEFAULT_QUALITY_RULES["overall_score_threshold"]
        if expected_overall < 1:
            expected_overall = expected_overall * 100
        assert monitor.thresholds["overall_score"] == expected_overall

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "quality_rules": {
                "completeness_threshold": 0.90,
                "accuracy_threshold": 0.85,
            },
            "thresholds": {
                "overall_score": 85,
            },
            "table_name": "my_table",
            "metrics": ["completeness", "accuracy"],
        }
        monitor = DataQualityMonitor(name="my_quality", config=config)
        assert monitor.name == "my_quality"
        assert monitor.quality_rules["completeness_threshold"] == 0.90
        assert monitor.quality_rules["accuracy_threshold"] == 0.85
        assert monitor.thresholds["overall_score"] == 85
        assert monitor.table_name == "my_table"
        assert monitor.metrics == ["completeness", "accuracy"]

    def test_init_threshold_conversion(self):
        """测试阈值转换 - 小数转百分比"""
        config = {
            "thresholds": {
                "overall_score": 0.80,  # 小数形式
            }
        }
        monitor = DataQualityMonitor(name="quality", config=config)
        assert monitor.thresholds["overall_score"] == 80  # 应该转为百分比

    def test_check_completeness_static_no_missing(self):
        """测试静态完整性检查 - 没有缺失值"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "col1": [1, 2, 3, 4, 5],
            "col2": [10, 20, 30, 40, 50],
        })
        completeness = monitor._check_completeness(df)
        assert completeness == 1.0

    def test_check_completeness_static_with_missing(self):
        """测试静态完整性检查 - 有缺失值"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "col1": [1, None, 3, None, 5],
            "col2": [10, 20, None, 40, 50],
        })
        # 总共有 5 * 2 = 10 个值，缺失 3 个，完整度 7/10 = 0.7
        completeness = monitor._check_completeness(df)
        assert completeness == pytest.approx(0.7)

    def test_check_completeness_static_empty(self):
        """测试静态完整性检查 - 空数据"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame()
        completeness = monitor._check_completeness(df)
        assert completeness == 0.0

    def test_check_accuracy_static_all_valid(self):
        """测试静态准确性检查 - 全部有效"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "stock_code": ["600000.SH", "000001.SZ"],
            "close": [10.5, 20.3],
            "volume": [1000000, 2000000],
        })
        accuracy = monitor._check_accuracy(df)
        assert accuracy == 1.0

    def test_check_accuracy_static_invalid_price(self):
        """测试静态准确性检查 - 有无效价格"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "stock_code": ["600000.SH", "000001.SZ"],
            "close": [10.5, -1.0],  # 负数价格无效
            "volume": [1000000, 2000000],
        })
        accuracy = monitor._check_accuracy(df)
        assert accuracy < 1.0

    def test_check_accuracy_static_invalid_code(self):
        """测试静态准确性检查 - 有无效股票代码"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "stock_code": ["600000", "BADCODE"],  # 缺少后缀，长度不对
            "close": [10.5, 20.3],
            "volume": [1000000, 2000000],
        })
        accuracy = monitor._check_accuracy(df)
        assert accuracy < 1.0

    def test_check_accuracy_static_invalid_volume(self):
        """测试静态准确性检查 - 有负成交量"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "stock_code": ["600000.SH", "000001.SZ"],
            "close": [10.5, 20.3],
            "volume": [1000000, -1000],  # 成交量负数
        })
        accuracy = monitor._check_accuracy(df)
        assert accuracy < 1.0

    def test_check_accuracy_static_empty(self):
        """测试静态准确性检查 - 空数据"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame()
        accuracy = monitor._check_accuracy(df)
        assert accuracy == 0.0

    def test_check_timeliness_static_on_time(self):
        """测试静态时效性检查 - 数据及时"""
        from common.utils import DateTimeUtils
        monitor = DataQualityMonitor(name="quality")
        now = DateTimeUtils.now()
        five_minutes_ago = now - timedelta(minutes=5)
        df = pd.DataFrame({
            "time": [five_minutes_ago],
        })
        timeliness = monitor._check_timeliness(df, max_delay_minutes=10)
        # 5分钟 < 10分钟，得分 = 1 - 5/10 = 0.5
        assert timeliness == 0.5

    def test_check_timeliness_static_late(self):
        """测试静态时效性检查 - 数据延迟"""
        from common.utils import DateTimeUtils
        monitor = DataQualityMonitor(name="quality")
        now = DateTimeUtils.now()
        twenty_minutes_ago = now - timedelta(minutes=20)
        df = pd.DataFrame({
            "time": [twenty_minutes_ago],
        })
        timeliness = monitor._check_timeliness(df, max_delay_minutes=10)
        # 20分钟 > 10分钟，得分 = max(0, 1 - 20/10) = 0
        assert timeliness == 0.0

    def test_check_timeliness_static_no_time_column(self):
        """测试静态时效性检查 - 没有时间列"""
        monitor = DataQualityMonitor(name="quality")
        df = pd.DataFrame({
            "close": [10.5, 20.3],
        })
        timeliness = monitor._check_timeliness(df)
        assert timeliness == 0.0

    def test_calculate_quality_score(self):
        """测试计算综合质量得分"""
        monitor = DataQualityMonitor(name="quality")
        metrics = {
            "completeness": 0.95,
            "accuracy": 0.98,
            "timeliness": 0.90,
            "consistency_rate": 0.96,
        }
        score = monitor._calculate_quality_score(metrics)
        # 权重: completeness(0.25) + accuracy(0.3) + timeliness(0.25) + consistency(0.2)
        # 0.95*0.25 = 0.2375
        # 0.98*0.3  = 0.294
        # 0.90*0.25 = 0.225
        # 0.96*0.2  = 0.192
        # total = 0.2375+0.294+0.225+0.192 = 0.9485 -> *100 = 94.85
        expected = (0.95 * 0.25 + 0.98 * 0.3 + 0.90 * 0.25 + 0.96 * 0.2) * 100
        assert score == pytest.approx(round(expected, 2))

    def test_calculate_quality_score_partial_metrics(self):
        """测试计算综合得分 - 部分指标缺失"""
        monitor = DataQualityMonitor(name="quality")
        metrics = {
            "completeness": 0.95,
            "accuracy": 0.98,
        }
        score = monitor._calculate_quality_score(metrics)
        # 只计算存在的指标，权重重新归一化
        # (0.95 * 0.25 + 0.98 * 0.3) / (0.25 + 0.3) * 100 = (0.2375 + 0.294) / 0.55 * 100 = 0.5315 / 0.55 * 100 ≈ 96.64
        expected = (0.95 * 0.25 + 0.98 * 0.3) / (0.25 + 0.3) * 100
        assert score == pytest.approx(round(expected, 2))

    def test_run_check_all_pass(self):
        """测试全部检查通过"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame({
            "stock_code": ["600000.SH", "000001.SZ"],
            "close": [10.5, 20.3],
            "volume": [1000000, 2000000],
        })
        mock_storage.get_storage = Mock(return_value=mock_clickhouse)

        config = {
            "metrics": ["completeness", "accuracy"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)

        result = monitor.run_check()
        assert result.success is True
        assert "综合得分" in result.message
        assert "overall_score" in result.metrics
        assert result.metrics["completeness"] == 1.0
        assert result.metrics["accuracy"] == 1.0

    def test_run_check_completeness_fail(self):
        """测试完整性不通过"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame({
            "stock_code": ["600000.SH", None],
            "close": [10.5, 20.3],
            "volume": [1000000, 2000000],
        })
        mock_storage.get_storage = Mock(return_value=mock_clickhouse)

        config = {
            "quality_rules": {
                "completeness_threshold": 0.90,
            },
            "metrics": ["completeness"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)

        result = monitor.run_check()
        assert result.success is False
        assert "数据完整度不足" in result.message
        assert result.alert_level == AlertLevel.WARNING

    def test_run_check_accuracy_fail(self):
        """测试准确性不通过"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame({
            "stock_code": ["600000.SH", "BAD"],
            "close": [10.5, -1.0],
            "volume": [1000000, 2000000],
        })
        mock_storage.get_storage = Mock(return_value=mock_clickhouse)

        config = {
            "quality_rules": {
                "accuracy_threshold": 0.90,
            },
            "metrics": ["accuracy"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)

        result = monitor.run_check()
        assert result.success is False
        assert "数据准确率不足" in result.message

    def test_run_check_overall_score_below_threshold(self):
        """测试综合得分低于阈值"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame({
            "stock_code": ["600000.SH"] * 10 + [None] * 5,
            "close": [10.5] * 10 + [20.3] * 5,
        })
        mock_storage.get_storage = Mock(return_value=mock_clickhouse)

        config = {
            "thresholds": {
                "overall_score": 80,
            },
            "metrics": ["completeness"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)

        result = monitor.run_check()
        # 完整性 = 10 / 15 ≈ 0.6667，得分 ≈ 66.67 < 80
        assert result.success is False
        # 可能因为完整性不足失败，也可能因为综合得分失败，都正确
        assert "数据完整度不足" in result.message or "综合得分未达标" in result.message

    def test_run_check_database_query_mode(self):
        """测试数据库聚合查询模式"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        # read 返回 None 触发聚合查询模式（我们就是要测试聚合查询）
        mock_clickhouse.read = Mock(return_value=None)
        # 第一次调用（完整性）返回 cnt，expected_count = 4 * 60 * 2500 = 600000
        # 0.95 * 600000 = 570000 → 95% 正好达到阈值
        # 第二次（准确性）返回total/invalid_price/invalid_volume
        mock_clickhouse.execute_sql.side_effect = [
            pd.DataFrame([{"cnt": 570000}]),  # 完整性查询 - 570000 / 600000 = 0.95 正好达到阈值
            pd.DataFrame([{"total": 1000, "invalid_price": 0, "invalid_volume": 0}]),  # 准确性查询
        ]
        mock_postgresql = Mock()

        mock_storage.get_storage = Mock(side_effect=lambda t: mock_clickhouse if t == "clickhouse" else mock_postgresql)

        config = {
            "metrics": ["completeness", "accuracy"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)
        # 已经确保 read 返回 None 触发聚合查询模式

        result = monitor.run_check()
        # 期望完整性 570000 / 600000 = 0.95，准确性 (1000 - 0 - 0)/1000 = 1.0，都高于默认阈值
        assert result.success is True
        assert "overall_score" in result.metrics

    def test_run_check_all_issues(self):
        """测试多项问题都不通过"""
        mock_storage = Mock()
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame({
            "stock_code": ["600000", None],
            "close": [10.5, -1.0],
            "volume": [1000000, -1000],
        })
        mock_storage.get_storage = Mock(return_value=mock_clickhouse)

        config = {
            "quality_rules": {
                "completeness_threshold": 0.95,
                "accuracy_threshold": 0.95,
            },
            "metrics": ["completeness", "accuracy"],
        }
        monitor = DataQualityMonitor(name="quality_check", config=config, storage_manager=mock_storage)

        result = monitor.run_check()
        assert result.success is False
        assert "数据完整度不足" in result.message
        assert "数据准确率不足" in result.message
