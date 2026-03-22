"""
Unit tests for fundamental_data_query.py
"""

import pandas as pd
import pytest
from unittest.mock import Mock, patch

from data_management.data_query.base_query import QueryCondition
from data_management.data_query.fundamental_data_query import FundamentalDataQuery


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

    query = FundamentalDataQuery(mock_storage)
    assert query.clickhouse_storage == mock_clickhouse
    assert query.postgresql_storage == mock_postgresql
    assert query.redis_storage == mock_redis
    assert "stock_basic" in query.table_config
    assert "financial_indicator" in query.table_config
    assert "dividend" in query.table_config


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

    query = FundamentalDataQuery(mock_storage)

    cond = QueryCondition()
    cond.stock_codes = ["600000.SH"]
    cond.filters = {"data_type": "financial_indicator"}

    cache_key = query._build_cache_key(cond)

    assert cache_key.startswith("fundamental_query:")
    assert "data_type" in cache_key
    assert "financial_indicator" in cache_key
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

    query = FundamentalDataQuery(mock_storage)

    cond = QueryCondition()
    cond.stock_codes = ["600000.SH", "000001.SZ"]
    cond.start_date = "2023-01-01"
    cond.end_date = "2023-12-31"
    cond.filters = {"data_type": "financial_indicator", "pe": (10, 50)}

    query_dict = query._build_query_dict(cond)

    assert query_dict["stock_code"] == ["600000.SH", "000001.SZ"]
    assert query_dict["report_date"] is not None
    assert query_dict["pe"] == (10, 50)
    assert "data_type" not in query_dict


def test_select_fields():
    """测试选择字段"""
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

    query = FundamentalDataQuery(mock_storage)

    df = pd.DataFrame({
        "stock_code": ["600000.SH", "000001.SZ"],
        "report_date": ["2023-12-31", "2023-12-31"],
        "pe": [15.5, 25.3],
        "pb": [1.5, 2.8],
        "roe": [12.5, 15.2],
    })

    result = query._select_fields(df, ["stock_code", "report_date", "pe"])
    assert list(result.columns) == ["stock_code", "report_date", "pe"]
    assert len(result) == 2


def test_query_unsupported_data_type():
    """测试查询不支持的数据类型"""
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

    query = FundamentalDataQuery(mock_storage)

    cond = QueryCondition()
    cond.filters = {"data_type": "unsupported"}

    result = query.query(cond)
    assert result.success is False
    assert "不支持的基本面数据类型" in result.message


def test_get_stock_basic_shortcut():
    """测试获取股票基础信息快捷方法"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_postgresql.read.return_value = pd.DataFrame({
        "stock_code": ["600000.SH", "000001.SZ"],
        "name": ["浦发银行", "平安银行"],
        "list_date": ["1999-11-10", "1991-04-03"],
    })
    mock_clickhouse.read.return_value = pd.DataFrame()
    mock_redis.read.return_value = None

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = FundamentalDataQuery(mock_storage)
    result = query.get_stock_basic()

    assert result.success is True
    df = result.to_df()
    assert len(df) == 2


def test_get_financial_indicator_shortcut():
    """测试获取财务指标快捷方法"""
    mock_storage = Mock()
    mock_clickhouse = Mock()
    mock_postgresql = Mock()
    mock_redis = Mock()
    mock_clickhouse.read.return_value = pd.DataFrame({
        "stock_code": ["600000.SH"] * 4,
        "report_date": ["2022Q1", "2022Q2", "2022Q3", "2022Q4"],
        "pe": [12.5, 13.2, 14.1, 15.5],
        "roe": [3.1, 6.2, 9.5, 12.8],
    })
    mock_postgresql.read.return_value = pd.DataFrame()
    mock_redis.read.return_value = None

    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
        "postgresql": mock_postgresql,
        "redis": mock_redis,
    }.get(t)

    query = FundamentalDataQuery(mock_storage)
    result = query.get_financial_indicator(
        stock_codes=["600000.SH"],
        start_date="2022-01-01",
        end_date="2022-12-31",
    )

    assert result.success is True
    df = result.to_df()
    assert len(df) == 4


def test_get_latest_financial_report():
    """测试获取最新财务报告"""
    mock_storage = Mock()
    mock_clickhouse = Mock()

    data = []
    for stock in ["600000.SH", "000001.SZ"]:
        for i in range(10):
            data.append({
                "stock_code": stock,
                "report_date": f"202{i//2}Q{i%2+1}",
                "pe": 15 + i,
            })

    mock_clickhouse.read.return_value = pd.DataFrame(data)
    mock_storage.get_storage_by_type.side_effect = lambda t: {
        "clickhouse": mock_clickhouse,
    }.get(t)

    query = FundamentalDataQuery(mock_storage)
    result = query.get_latest_financial_report(["600000.SH", "000001.SZ"], report_count=4)

    assert result.success is True
    df = result.to_df()
    # 每个股票只保留最新4个报告
    assert len(df) == 8
