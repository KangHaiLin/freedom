"""
Unit tests for collection_monitor.py
"""

from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest

from data_management.data_monitoring.base_monitor import AlertLevel, MonitorResult
from data_management.data_monitoring.collection_monitor import CollectionMonitor


class TestCollectionMonitor:
    """测试数据采集监控"""

    def test_init_default(self):
        """测试默认初始化"""
        monitor = CollectionMonitor(name="collection_monitor")
        assert monitor.name == "collection_monitor"
        assert "success_rate_threshold" in monitor.collection_rules
        assert monitor.collection_rules["success_rate_threshold"] == 0.95
        assert monitor.collection_rules["speed_threshold"] == 1000
        assert monitor.collection_rules["error_rate_threshold"] == 0.05
        assert monitor.collection_rules["task_timeout"] == 300

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = {
            "success_rate_threshold": 0.90,
            "speed_threshold": 500,
            "error_rate_threshold": 0.10,
            "task_timeout": 600,
        }
        mock_ds_manager = Mock()
        monitor = CollectionMonitor(
            name="my_collection",
            config=config,
            data_source_manager=mock_ds_manager
        )
        assert monitor.name == "my_collection"
        assert monitor.collection_rules["success_rate_threshold"] == 0.90
        assert monitor.collection_rules["speed_threshold"] == 500
        assert monitor.collection_rules["error_rate_threshold"] == 0.10
        assert monitor.collection_rules["task_timeout"] == 600
        assert monitor.data_source_manager == mock_ds_manager

    def test_run_check_all_success(self):
        """测试所有检查都通过"""
        mock_ds_manager = Mock()
        mock_ds_manager.get_statistics.return_value = {
            "total_requests": 100,
            "success_requests": 98,
            "data_volume_per_minute": 2000,
        }

        class MockSource:
            def is_available(self):
                return True
            availability = 1.0
            avg_response_time = 100

        mock_ds_manager.sources = [MockSource(), MockSource()]

        monitor = CollectionMonitor(
            name="collection",
            config={"success_rate_threshold": 0.95},
            data_source_manager=mock_ds_manager
        )

        result = monitor.run_check()
        assert result.success is True
        assert "检查通过" in result.message
        assert result.metrics["success_rate"] == 0.98
        assert result.metrics["available_sources"] == 2

    def test_run_check_low_success_rate(self):
        """测试成功率不足"""
        mock_ds_manager = Mock()
        mock_ds_manager.get_statistics.return_value = {
            "total_requests": 100,
            "success_requests": 80,
            "data_volume_per_minute": 2000,
        }

        class MockSource:
            def is_available(self):
                return True
            availability = 1.0
            avg_response_time = 100

        mock_ds_manager.sources = [MockSource(), MockSource()]

        monitor = CollectionMonitor(
            name="collection",
            config={"success_rate_threshold": 0.95},
            data_source_manager=mock_ds_manager
        )

        result = monitor.run_check()
        assert result.success is False
        assert result.alert_level == AlertLevel.WARNING
        assert "采集成功率不足" in result.message
        assert "80.00%" in result.message

    def test_run_check_no_available_sources(self):
        """测试没有可用数据源"""
        mock_ds_manager = Mock()
        mock_ds_manager.get_statistics.return_value = {
            "total_requests": 100,
            "success_requests": 98,
            "data_volume_per_minute": 2000,
        }

        class MockSource:
            def is_available(self):
                return False
            availability = 0.0
            avg_response_time = 100

        mock_ds_manager.sources = [MockSource(), MockSource()]

        monitor = CollectionMonitor(
            name="collection",
            data_source_manager=mock_ds_manager
        )

        result = monitor.run_check()
        assert result.success is False
        assert "数据源不可用" in result.message

    def test_check_data_source_status_all_available(self):
        """测试数据源状态检查 - 全部可用"""
        mock_ds_manager = Mock()
        mock_ds_manager.get_source_status.return_value = [
            {"source": "tushare", "is_available": True},
            {"source": "akshare", "is_available": True},
        ]

        monitor = CollectionMonitor(
            name="collection",
            data_source_manager=mock_ds_manager
        )

        result = monitor._check_data_source_status()
        assert result["success"] is True
        assert result["metrics"]["total_sources"] == 2
        assert result["metrics"]["available_sources"] == 2
        assert result["message"] == ""

    def test_check_data_source_status_some_unavailable(self):
        """测试数据源状态检查 - 部分不可用"""
        mock_ds_manager = Mock()
        mock_ds_manager.get_source_status.return_value = [
            {"source": "tushare", "is_available": True},
            {"source": "wind", "is_available": False},
        ]

        monitor = CollectionMonitor(
            name="collection",
            data_source_manager=mock_ds_manager
        )

        result = monitor._check_data_source_status()
        assert result["success"] is False
        assert "wind" in result["message"]
        assert result["metrics"]["total_sources"] == 2
        assert result["metrics"]["available_sources"] == 1

    def test_check_collection_success_rate_all_success(self):
        """测试采集成功率检查 - 全部成功"""
        mock_clickhouse = Mock()
        df = pd.DataFrame([
            {"status": "success", "cnt": 95},
            {"status": "fail", "cnt": 5},
        ])
        mock_clickhouse.execute_sql.return_value = df

        mock_storage = Mock()
        mock_storage.get_storage_by_type = Mock(return_value=mock_clickhouse)

        monitor = CollectionMonitor(name="collection")
        monitor.clickhouse_storage = mock_clickhouse

        result = monitor._check_collection_success_rate()
        assert result["success"] is True
        assert result["metrics"]["success_rate"] == 0.95
        assert result["metrics"]["error_rate"] == 0.05

    def test_check_collection_success_rate_below_threshold(self):
        """测试采集成功率检查 - 低于阈值"""
        mock_clickhouse = Mock()
        df = pd.DataFrame([
            {"status": "success", "cnt": 80},
            {"status": "fail", "cnt": 20},
        ])
        mock_clickhouse.execute_sql.return_value = df

        monitor = CollectionMonitor(name="collection")
        monitor.clickhouse_storage = mock_clickhouse

        result = monitor._check_collection_success_rate()
        assert result["success"] is False
        assert "采集成功率不足" in result["message"]
        assert "80.00%" in result["message"]

    def test_check_collection_success_rate_error_rate_too_high(self):
        """测试错误率过高"""
        mock_clickhouse = Mock()
        df = pd.DataFrame([
            {"status": "success", "cnt": 90},
            {"status": "fail", "cnt": 10},
        ])
        mock_clickhouse.execute_sql.return_value = df

        monitor = CollectionMonitor(name="collection")
        monitor.collection_rules["error_rate_threshold"] = 0.05
        monitor.clickhouse_storage = mock_clickhouse

        result = monitor._check_collection_success_rate()
        assert result["success"] is False
        assert "错误率过高" in result["message"]
        assert "10.00%" in result["message"]

    def test_check_collection_success_rate_empty(self):
        """测试没有数据时默认成功"""
        mock_clickhouse = Mock()
        mock_clickhouse.execute_sql.return_value = pd.DataFrame()

        monitor = CollectionMonitor(name="collection")
        monitor.clickhouse_storage = mock_clickhouse

        result = monitor._check_collection_success_rate()
        assert result["success"] is True
        assert result["metrics"]["success_rate"] == 1.0

    def test_check_collection_speed_good(self):
        """测试采集速度检查 - 速度正常"""
        mock_redis = Mock()
        mock_redis.read.return_value = {
            "collection_speed:source1": 1500,
            "collection_speed:source2": 2000,
        }

        monitor = CollectionMonitor(name="collection")
        monitor.collection_rules["speed_threshold"] = 1000
        monitor.redis_storage = mock_redis

        result = monitor._check_collection_speed()
        assert result["success"] is True
        assert "avg_speed" in result["metrics"]
        assert result["metrics"]["avg_speed"] == 1750

    def test_check_collection_speed_too_slow(self):
        """测试采集速度检查 - 速度过慢"""
        mock_redis = Mock()
        mock_redis.read.return_value = {
            "collection_speed:source1": 500,
            "collection_speed:source2": 600,
        }

        monitor = CollectionMonitor(name="collection")
        monitor.collection_rules["speed_threshold"] = 1000
        monitor.redis_storage = mock_redis

        result = monitor._check_collection_speed()
        assert result["success"] is False
        assert "采集速度过慢" in result["message"]
        assert "550" in result["message"]

    def test_check_collection_speed_no_records(self):
        """测试没有速度记录默认成功"""
        mock_redis = Mock()
        mock_redis.read.return_value = {}

        monitor = CollectionMonitor(name="collection")
        monitor.redis_storage = mock_redis

        result = monitor._check_collection_speed()
        assert result["success"] is True

    def test_check_task_status_no_timeout(self):
        """测试任务状态检查 - 没有超时"""
        mock_redis = Mock()
        now = datetime.now().timestamp()
        mock_redis.read.return_value = {
            "task:1": {"status": "running", "start_time": now - 60},
            "task:2": {"status": "running", "start_time": now - 100},
        }

        monitor = CollectionMonitor(name="collection")
        monitor.collection_rules["task_timeout"] = 300
        monitor.redis_storage = mock_redis

        result = monitor._check_task_status()
        assert result["success"] is True
        assert result["metrics"]["running_tasks_count"] == 2
        assert result["metrics"]["timeout_tasks_count"] == 0

    def test_check_task_status_has_timeout(self):
        """测试任务状态检查 - 有超时"""
        mock_redis = Mock()
        now = datetime.now().timestamp()
        mock_redis.read.return_value = {
            "task:1": {"status": "running", "start_time": now - 60},
            "task:2": {"status": "running", "start_time": now - 400},
        }

        monitor = CollectionMonitor(name="collection")
        monitor.collection_rules["task_timeout"] = 300
        monitor.redis_storage = mock_redis

        result = monitor._check_task_status()
        assert result["success"] is False
        assert "采集任务超时" in result["message"]
        assert "task:2" in result["message"]
        assert result["metrics"]["timeout_tasks_count"] == 1

    def test_check_data_source_health(self):
        """测试数据源健康统计"""
        mock_ds_manager = Mock()

        class Source1:
            def is_available(self):
                return True
            availability = 1.0
            avg_response_time = 100

        class Source2:
            def is_available(self):
                return False
            availability = 0.0
            avg_response_time = 200

        mock_ds_manager.sources = [Source1(), Source2()]

        monitor = CollectionMonitor(
            name="collection",
            data_source_manager=mock_ds_manager
        )

        result = monitor._check_data_source_health()
        assert result["total_sources"] == 2
        assert result["available_sources"] == 1
        assert result["average_availability"] == 0.5
        assert result["average_response_time"] == 150

    def test_check_data_source_health_empty(self):
        """测试空数据源列表"""
        mock_ds_manager = Mock()
        mock_ds_manager.sources = []

        monitor = CollectionMonitor(
            name="collection",
            data_source_manager=mock_ds_manager
        )

        result = monitor._check_data_source_health()
        assert result["total_sources"] == 0
        assert result["available_sources"] == 0
