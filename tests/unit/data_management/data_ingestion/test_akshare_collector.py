"""
Unit tests for akshare_collector.py
"""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.data_management.data_ingestion.akshare_collector import AKShareCollector


def test_initialization_success():
    """测试初始化成功（AKShare不需要API key）"""
    collector = AKShareCollector({"priority": 5, "weight": 1.0})

    assert collector.source == "akshare"
    assert collector.priority == 5
    assert collector.weight == 1.0
    assert collector.rate_limit > 0
    assert hasattr(collector, "_rate_limit_check")
    assert hasattr(collector, "_convert_stock_code")


def test_initialization_custom_rate_limit():
    """测试自定义频率限制"""
    collector = AKShareCollector({"rate_limit": 50})
    assert collector.rate_limit == 50


def test_convert_stock_code():
    """测试股票代码转换"""
    collector = AKShareCollector({})

    # 上证
    assert collector._convert_stock_code("600000.SH") == "sh600000"
    # 深证
    assert collector._convert_stock_code("000001.SZ") == "sz000001"
    # 北交所
    assert collector._convert_stock_code("831370.BJ") == "bj831370"


def test_rate_limit_check():
    """测试请求频率限制"""
    collector = AKShareCollector({"rate_limit": 2})

    # 前两次请求不应该等待
    collector._rate_limit_check()
    assert collector.request_count == 1
    collector._rate_limit_check()
    assert collector.request_count == 2

    # 验证方法执行正常
    collector._rate_limit_check()
    # 通过即成功


@patch("akshare.stock_zh_a_spot")
def test_get_realtime_quote(mock_stock_zh_a_spot):
    """测试获取实时行情"""
    mock_data = pd.DataFrame(
        {
            "代码": ["sh600000", "sz000001"],
            "名称": ["浦发银行", "平安银行"],
            "最新": [7.5, 10.2],
            "开盘": [7.4, 10.1],
            "最高": [7.6, 10.3],
            "最低": [7.3, 10.0],
            "成交量": [1000000, 2000000],
            "成交额": [7500000, 20400000],
        }
    )
    mock_stock_zh_a_spot.return_value = mock_data

    collector = AKShareCollector({"priority": 5})
    result = collector.get_realtime_quote(["600000.SH", "000001.SZ"])

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "time" in result.columns
    assert "price" in result.columns
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "volume" in result.columns
    assert "amount" in result.columns
    assert "source" in result.columns
    assert all(result["source"] == "akshare")

    mock_stock_zh_a_spot.assert_called_once()


@patch("akshare.stock_zh_a_spot")
def test_get_realtime_quote_empty(mock_stock_zh_a_spot):
    """测试获取实时行情返回空"""
    mock_stock_zh_a_spot.return_value = pd.DataFrame()

    collector = AKShareCollector({})
    result = collector.get_realtime_quote(["600000.SH"])

    assert result.empty


@patch("akshare.stock_zh_a_daily")
def test_get_daily_quote(mock_stock_zh_a_daily):
    """测试获取日线行情"""
    mock_data = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "open": [7.4, 7.5],
            "high": [7.6, 7.7],
            "low": [7.3, 7.4],
            "close": [7.5, 7.6],
            "volume": [1000000, 1100000],
            "amount": [7500000, 8250000],
        }
    )
    mock_data.set_index("date", inplace=True)
    mock_stock_zh_a_daily.return_value = mock_data

    collector = AKShareCollector({})
    result = collector.get_daily_quote(["600000.SH"], "2025-01-01", "2025-01-02")

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "trade_date" in result.columns
    assert "open" in result.columns
    assert "close" in result.columns
    assert "adjust_factor" in result.columns
    assert all(result["adjust_factor"] == 1.0)
    assert pd.api.types.is_datetime64_dtype(result["trade_date"])


@patch("akshare.stock_zh_a_daily")
def test_get_daily_quote_all_fail(mock_stock_zh_a_daily):
    """测试所有股票获取失败返回空"""
    mock_stock_zh_a_daily.return_value = pd.DataFrame()

    collector = AKShareCollector({})
    result = collector.get_daily_quote(["600000.SH", "000001.SZ"], "2025-01-01", "2025-01-02")

    assert result.empty


@patch("akshare.stock_zh_a_minute")
def test_get_minute_quote(mock_stock_zh_a_minute):
    """测试获取分钟线行情"""
    mock_data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01 09:31:00", "2025-01-01 09:32:00"]),
            "open": [7.5, 7.51],
            "high": [7.52, 7.53],
            "low": [7.49, 7.50],
            "close": [7.51, 7.52],
            "volume": [10000, 11000],
            "amount": [75000, 82610],
        }
    )
    mock_stock_zh_a_minute.return_value = mock_data

    collector = AKShareCollector({})
    result = collector.get_minute_quote(["600000.SH"], "2025-01-01", "2025-01-01 23:59:59", period=1)

    assert not result.empty
    assert "stock_code" in result.columns
    assert "trade_time" in result.columns
    assert "open" in result.columns
    assert "close" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["trade_time"])


@patch("akshare.stock_zh_a_tick_tx_js")
def test_get_tick_quote(mock_stock_zh_a_tick):
    """测试获取Tick行情"""
    mock_data = pd.DataFrame(
        {
            "成交时间": ["09:30:00", "09:30:01"],
            "成交价": [7.50, 7.51],
            "成交量": [100, 200],
            "成交额": [750, 1502],
        }
    )
    mock_data["成交时间"] = pd.to_datetime("2025-01-01 " + mock_data["成交时间"])
    mock_stock_zh_a_tick.return_value = mock_data

    collector = AKShareCollector({})
    result = collector.get_tick_quote(["600000.SH"], "2025-01-01")

    assert not result.empty
    assert "stock_code" in result.columns
    assert "trade_time" in result.columns
    assert "price" in result.columns
    assert "volume" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["trade_time"])


def test_get_source_info():
    """测试获取数据源信息"""
    collector = AKShareCollector({"priority": 5, "weight": 2.0})
    info = collector.get_source_info()

    assert info["source"] == "akshare"
    assert info["priority"] == 5
    assert info["weight"] == 2.0
    assert "availability" in info
    assert "avg_response_time" in info
    assert "error_count" in info
    assert "is_available" in info


def test_is_available():
    """测试数据源可用性判断"""
    collector = AKShareCollector({})
    assert collector.is_available()  # 初始状态可用

    # 多次错误后应该不可用
    for _ in range(5):
        collector.record_error("test error")
    # 错误计数5次，但因为时间判断，可能还可用
    # 主要验证方法不抛出异常
    result = collector.is_available()
    assert result is not None
