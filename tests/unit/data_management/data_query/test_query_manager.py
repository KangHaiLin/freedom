"""
Unit tests for query_manager.py
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from common.exceptions import QueryException
from data_management.data_query.query_manager import QueryManager, query_manager


def test_initialization():
    """测试初始化"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.return_value = mock_clickhouse

        manager = QueryManager()
        assert "market" in manager.query_services
        assert "fundamental" in manager.query_services
        assert manager.enable_cache is not None


def test_get_query_service_exists():
    """测试获取存在的查询服务"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.return_value = mock_clickhouse

        manager = QueryManager()
        service = manager.get_query_service("market")
        assert service is not None

        service = manager.get_query_service("fundamental")
        assert service is not None


def test_get_query_service_not_exists():
    """测试获取不存在的查询服务应该抛出异常"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.return_value = mock_clickhouse

        manager = QueryManager()
        with pytest.raises(QueryException, match="不支持的查询服务类型"):
            manager.get_query_service("nonexistent")


def test_query_success():
    """测试成功查询"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": ["2024-01-01", "2024-01-02"],
            "stock_code": ["600000.SH", "600000.SH"],
            "close": [10.5, 10.6],
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    def get_storage_by_type(t):
        if t == "clickhouse":
            return mock_clickhouse
        elif t == "postgresql":
            return mock_postgresql
        elif t == "redis":
            return mock_redis
        else:
            return None

    mock_storage.get_storage_by_type.side_effect = get_storage_by_type

    manager = QueryManager(storage_manager_inject=mock_storage)
    assert manager.storage_manager is mock_storage

    result = manager.query(
        service_type="market",
        stock_codes=["600000.SH"],
        start_date="2024-01-01",
        end_date="2024-01-31",
        filters={"data_type": "daily"},
    )

    assert result.success is True
    df = result.to_df()
    assert len(df) == 2
    mock_clickhouse.read.assert_called_once()


def test_query_invalid_condition():
    """测试查询条件无效"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.side_effect = lambda t: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }.get(t)

        manager = QueryManager()
        result = manager.query(
            service_type="market",
            stock_codes=["600000.SH"],
            start_date="2024-01-31",
            end_date="2024-01-01",  # 开始 > 结束，无效
            filters={"data_type": "daily"},
        )

        assert result.success is False
        assert "开始日期不能大于结束日期" in result.message


def test_batch_query():
    """测试批量查询"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": ["2024-01-01"],
            "stock_code": ["600000.SH"],
            "close": [10.5],
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    def get_storage_by_type(t):
        if t == "clickhouse":
            return mock_clickhouse
        elif t == "postgresql":
            return mock_postgresql
        elif t == "redis":
            return mock_redis
        else:
            return None

    mock_storage.get_storage_by_type.side_effect = get_storage_by_type

    manager = QueryManager(storage_manager_inject=mock_storage)
    queries = [
        {
            "service_type": "market",
            "stock_codes": ["600000.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "filters": {"data_type": "daily"},
        },
        {
            "service_type": "market",
            "stock_codes": ["000001.SZ"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "filters": {"data_type": "daily"},
        },
    ]

    results = manager.batch_query(queries)
    assert len(results) == 2
    assert all(r.success for r in results)


def test_batch_query_with_error():
    """测试批量查询包含错误查询"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": ["2024-01-01"],
            "stock_code": ["600000.SH"],
            "close": [10.5],
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    def get_storage_by_type(t):
        if t == "clickhouse":
            return mock_clickhouse
        elif t == "postgresql":
            return mock_postgresql
        elif t == "redis":
            return mock_redis
        else:
            return None

    mock_storage.get_storage_by_type.side_effect = get_storage_by_type

    manager = QueryManager(storage_manager_inject=mock_storage)
    queries = [
        {
            "service_type": "market",
            "stock_codes": ["600000.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "filters": {"data_type": "daily"},
        },
        {
            "service_type": "invalid",
            "stock_codes": ["000001.SZ"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        },
    ]

    results = manager.batch_query(queries)
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is False


def test_health_check():
    """测试健康检查"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_postgresql.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.side_effect = lambda t: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }.get(t)
        mock_storage.health_check.return_value = {"status": "healthy"}

        manager = QueryManager()
        health = manager.health_check()

        assert health["status"] == "healthy"
        assert "query_services" in health
        assert "market" in health["query_services"]
        assert "storage_health" in health


def test_global_instance_exists():
    """测试全局实例存在"""
    assert query_manager is not None
    assert isinstance(query_manager, QueryManager)


# 快捷方法测试 - 只测试基本调用，主要逻辑已经在具体查询类测试
def test_get_realtime_quote_shortcut():
    """测试快捷获取实时行情"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.side_effect = lambda t: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }.get(t)

        manager = QueryManager()
        result = manager.get_realtime_quote(["600000.SH"])
        assert result is not None


def test_get_daily_quote_shortcut():
    """测试快捷获取日线行情"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_clickhouse.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.side_effect = lambda t: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }.get(t)

        manager = QueryManager()
        result = manager.get_daily_quote(["600000.SH"], "2024-01-01", "2024-01-31")
        assert result is not None


def test_get_stock_basic_shortcut():
    """测试快捷获取股票基础信息"""
    with patch("data_management.data_query.query_manager.storage_manager") as mock_storage:
        mock_clickhouse = Mock()
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_postgresql.read.return_value = pd.DataFrame()
        mock_storage.get_storage_by_type.side_effect = lambda t: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }.get(t)

        manager = QueryManager()
        result = manager.get_stock_basic()
        assert result is not None
