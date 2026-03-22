"""
Unit tests for market_data_query.py
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from data_management.data_query.base_query import QueryCondition
from data_management.data_query.market_data_query import MarketDataQuery


def test_initialization():
    """测试初始化"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = MarketDataQuery(mock_storage)
    assert query.clickhouse_storage == mock_clickhouse
    assert query.postgresql_storage == mock_postgresql
    assert query.redis_storage == mock_redis
    assert "daily" in query.table_config
    assert "tick" in query.table_config


def test_build_cache_key():
    """测试构建缓存键"""
    mock_storage = Mock()
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

    query = MarketDataQuery(mock_storage)

    cond = QueryCondition()
    cond.stock_codes = ["600000.SH"]
    cond.start_date = "2024-01-01"
    cond.filters = {"data_type": "daily"}

    cache_key = query._build_cache_key(cond)

    assert cache_key.startswith("market_query:")
    assert "data_type" in cache_key
    assert "daily" in cache_key
    assert "600000.SH" in cache_key


def test_build_query_dict():
    """测试构建查询字典"""
    mock_storage = Mock()
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

    query = MarketDataQuery(mock_storage)

    cond = QueryCondition()
    cond.stock_codes = ["600000.SH", "000001.SZ"]
    cond.start_date = "2024-01-01"
    cond.end_date = "2024-01-31"
    cond.filters = {"data_type": "daily", "close": (10, 20)}

    query_dict = query._build_query_dict(cond, "daily")

    assert query_dict["stock_code"] == ["600000.SH", "000001.SZ"]
    assert query_dict["trade_date"] is not None
    assert query_dict["close"] == (10, 20)
    assert "data_type" not in query_dict


def test_get_time_column():
    """测试获取时间列名"""
    mock_storage = Mock()
    mock_storage.get_storage_by_type.return_value = Mock()
    query = MarketDataQuery(mock_storage)

    assert query._get_time_column("realtime") == "time"
    assert query._get_time_column("daily") == "trade_date"
    assert query._get_time_column("minute") == "trade_time"
    assert query._get_time_column("tick") == "trade_time"


def test_select_fields():
    """测试选择字段"""
    mock_storage = Mock()
    mock_storage.get_storage_by_type.return_value = Mock()
    query = MarketDataQuery(mock_storage)

    df = pd.DataFrame(
        {
            "trade_date": ["2024-01-01", "2024-01-02"],
            "open": [10, 11],
            "high": [11, 12],
            "low": [9, 10],
            "close": [10.5, 11.5],
            "volume": [1000, 1200],
        }
    )

    # 选择部分字段
    result = query._select_fields(df, ["trade_date", "close", "volume"])
    assert list(result.columns) == ["trade_date", "close", "volume"]
    assert len(result) == 2

    # 选择全部保留
    result = query._select_fields(df, None)
    assert len(result.columns) == 6

    # 不存在的字段应该被忽略
    result = query._select_fields(df, ["close", "nonexistent"])
    assert list(result.columns) == ["close"]


def test_query_unsupported_data_type():
    """测试查询不支持的数据类型应该返回失败"""
    mock_storage = Mock()
    mock_storage.get_storage_by_type.return_value = Mock()
    query = MarketDataQuery(mock_storage)

    cond = QueryCondition()
    cond.filters = {"data_type": "unsupported"}

    result = query.query(cond)
    assert result.success is False
    assert "不支持的行情数据类型" in result.message


def test_query_cached_result():
    """测试缓存命中应该直接返回缓存"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_redis = Mock()

    cached_data = [{"trade_date": "2024-01-01", "stock_code": "600000.SH", "close": 10.5}]
    mock_redis.read.return_value = cached_data

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "redis": mock_redis,
    }.get(t)

    query = MarketDataQuery(mock_storage)
    cond = QueryCondition()
    cond.stock_codes = ["600000.SH"]
    cond.filters = {"data_type": "daily"}

    result = query.query(cond)
    assert result.success is True
    assert result.message == "缓存命中"
    assert len(result.data) == 1
    # 验证clickhouse没有被调用
    mock_clickhouse.read.assert_not_called()


def test_get_daily_quote_shortcut():
    """测试快捷获取日线行情方法"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": pd.date_range("2024-01-01", "2024-01-10"),
            "stock_code": ["600000.SH"] * 10,
            "close": [10 + i for i in range(10)],
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = MarketDataQuery(mock_storage)
    result = query.get_daily_quote(
        stock_codes=["600000.SH"], start_date="2024-01-01", end_date="2024-01-10", fields=["trade_date", "close"]
    )

    assert result.success is True
    df = result.to_df()
    assert len(df) == 10
    assert "close" in df.columns


def test_get_latest_daily_quote():
    """测试获取最近N天日线"""
    from datetime import datetime, timedelta

    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(10)]
    dates.reverse()
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": dates,
            "stock_code": ["600000.SH"] * 10,
            "close": [10 + i for i in range(10)],
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = MarketDataQuery(mock_storage)
    result = query.get_latest_daily_quote(["600000.SH"], days=5, fields=["trade_date", "close", "stock_code"])

    assert result.success is True
    df = result.to_df()
    # 应该只返回最近5天
    assert len(df) == 5


def test_calculate_ma():
    """测试计算均线"""
    from datetime import datetime, timedelta

    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in reversed(range(100))]
    close_prices = [10 + i * 0.1 for i in range(100)]
    mock_clickhouse.read.return_value = pd.DataFrame(
        {
            "trade_date": dates,
            "close": close_prices,
        }
    )
    mock_redis.read.return_value = None  # 缓存未命中

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = MarketDataQuery(mock_storage)
    result = query.calculate_ma("600000.SH", periods=[5, 10], days=50)

    assert result.success is True
    df = result.to_df()
    assert len(df) == 50
    assert "ma5" in df.columns
    assert "ma10" in df.columns
    # 最后一天应该有值
    assert not pd.isna(df.iloc[-1]["ma5"])
    assert not pd.isna(df.iloc[-1]["ma10"])
