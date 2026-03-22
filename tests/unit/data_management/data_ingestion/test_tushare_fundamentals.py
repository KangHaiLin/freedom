"""
Unit tests for tushare_fundamentals.py
"""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from common.exceptions import DataSourceException
from src.data_management.data_ingestion.tushare_fundamentals import TushareFundamentalsCollector


def test_initialization_no_api_key():
    """测试没有API key应该抛出异常"""
    with pytest.raises(DataSourceException, match="Tushare API Key未配置"):
        TushareFundamentalsCollector({})


@patch("tushare.pro_api")
def test_initialization_success(mock_pro_api):
    """测试初始化成功"""
    mock_pro = MagicMock()
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})

    assert collector.api_key == "test_key"
    assert collector.pro == mock_pro
    assert collector.rate_limit > 0


@patch("tushare.pro_api")
def test_get_stock_basic(mock_pro_api):
    """测试获取股票基本信息"""
    # 创建mock返回数据
    mock_data = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "600000.SH"],
            "name": ["平安银行", "浦发银行"],
            "fullname": ["平安银行股份有限公司", "上海浦东发展银行股份有限公司"],
            "industry": ["银行", "银行"],
            "market": ["主板", "主板"],
            "list_date": ["19910403", "19991110"],
            "delist_date": [None, None],
            "is_hs": ["S", "S"],
        }
    )

    mock_pro = MagicMock()
    mock_pro.stock_basic.return_value = mock_data
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_stock_basic(list_status="L")

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "name" in result.columns
    assert "list_date" in result.columns
    # 检查日期转换
    assert pd.api.types.is_datetime64_dtype(result["list_date"])

    mock_pro.stock_basic.assert_called_once_with(list_status="L")


@patch("tushare.pro_api")
def test_get_stock_basic_empty(mock_pro_api):
    """测试获取股票列表返回空"""
    mock_pro = MagicMock()
    mock_pro.stock_basic.return_value = pd.DataFrame()
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_stock_basic(list_status="L")

    assert result.empty


@patch("tushare.pro_api")
def test_get_daily_basic(mock_pro_api):
    """测试获取每日基本面"""
    # 创建mock数据
    mock_data = pd.DataFrame(
        {
            "ts_code": ["000001SZ", "000001SZ"],
            "trade_date": ["20250101", "20250102"],
            "total_share": [19405652231.0, 19405652231.0],
            "float_share": [19405652231.0, 19405652231.0],
            "total_mv": [200000000000.0, 205000000000.0],
            "circ_mv": [200000000000.0, 205000000000.0],
            "pe": [10.5, 10.8],
            "pb": [1.2, 1.25],
            "turnover_rate": [0.8, 0.9],
        }
    )

    mock_pro = MagicMock()
    mock_pro.daily_basic.return_value = mock_data
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_daily_basic(["000001.SZ"], "2025-01-01", "2025-01-02")

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "trade_date" in result.columns
    assert "pe" in result.columns
    assert "pb" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["trade_date"])


@patch("tushare.pro_api")
def test_get_daily_basic_all_fail(mock_pro_api):
    """测试所有股票都失败返回空"""
    mock_pro = MagicMock()
    mock_pro.daily_basic.return_value = pd.DataFrame()
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_daily_basic(["000001.SZ", "600000.SH"], "2025-01-01", "2025-01-02")

    assert result.empty


@patch("tushare.pro_api")
def test_get_financial_indicator(mock_pro_api):
    """测试获取财务指标"""
    mock_data = pd.DataFrame(
        {
            "ts_code": ["000001SZ"],
            "end_date": ["20241231"],
            "ann_date": ["20250315"],
            "roe": [15.5],
            "roa": [0.8],
            "gross_margin": [35.0],
            "net_profit_margin": [15.0],
            "debt_to_assets": [92.0],
            "current_ratio": [0.9],
            "quick_ratio": [0.8],
            "eps": [1.5],
            "bvps": [12.5],
        }
    )

    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = mock_data
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_financial_indicator(["000001.SZ"], "2024-01-01", "2024-12-31")

    assert not result.empty
    assert "stock_code" in result.columns
    assert "roe" in result.columns
    assert "roa" in result.columns
    assert "gross_margin" in result.columns
    assert "net_margin" in result.columns  # 检查重命名
    assert "debt_ratio" in result.columns


@patch("tushare.pro_api")
def test_get_dividend(mock_pro_api):
    """测试获取分红数据"""
    mock_data = pd.DataFrame(
        {
            "ts_code": ["000001SZ"],
            "div_proc": ["20240515"],
            "ex_date": ["20240516"],
            "record_date": ["20240517"],
            "pay_date": ["20240520"],
            "cash_div": [0.25],
            "stock_div": [0],
        }
    )

    mock_pro = MagicMock()
    mock_pro.dividend.return_value = mock_data
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_dividend(["000001.SZ"])

    assert not result.empty
    assert "stock_code" in result.columns
    assert "ex_date" in result.columns
    assert "dividend_per_share" in result.columns
    assert "bonus_ratio" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["ex_date"])


@patch("tushare.pro_api")
def test_get_margin_trading(mock_pro_api):
    """测试获取融资融券数据"""
    mock_data = pd.DataFrame(
        {
            "trade_date": ["20250101", "20250102"],
            "ts_code": ["000001.SZ", "000001.SZ"],
            "rzye": [100000000, 101000000],
            "rqye": [50000000, 51000000],
        }
    )

    mock_pro = MagicMock()
    mock_pro.margin.return_value = mock_data
    mock_pro_api.return_value = mock_pro

    collector = TushareFundamentalsCollector({"api_key": "test_key"})
    result = collector.get_margin_trading(["000001.SZ"], "2025-01-01", "2025-01-02")

    assert not result.empty
    assert "stock_code" in result.columns
    assert "trade_date" in result.columns
    assert "margin_balance" in result.columns
    assert "short_balance" in result.columns


def test_rate_limit_check():
    """测试请求频率限制"""
    with patch("tushare.pro_api"):
        collector = TushareFundamentalsCollector({"api_key": "test_key", "rate_limit": 2})

        # 前两次请求不应该等待
        collector._rate_limit_check()
        assert collector.request_count == 1
        collector._rate_limit_check()
        assert collector.request_count == 2

        # 第三次应该触发频率限制检查（测试时时间很近，应该会重置计数）
        # 这个测试主要验证方法不抛出异常
        collector._rate_limit_check()
        # 通过即成功
