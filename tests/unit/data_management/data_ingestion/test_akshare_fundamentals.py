"""
Unit tests for akshare_fundamentals.py
"""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.data_management.data_ingestion.akshare_fundamentals import AKShareFundamentalsCollector


def test_initialization_success():
    """测试初始化成功（AKShare不需要API key）"""
    collector = AKShareFundamentalsCollector({"priority": 5, "weight": 1.0})

    assert collector.source == "akshare"
    assert collector.priority == 5
    assert collector.weight == 1.0
    assert collector.rate_limit > 0
    assert hasattr(collector, "_rate_limit_check")
    assert hasattr(collector, "_convert_stock_code_ak")


def test_initialization_custom_rate_limit():
    """测试自定义频率限制"""
    collector = AKShareFundamentalsCollector({"rate_limit": 50})
    assert collector.rate_limit == 50


def test_convert_stock_code():
    """测试股票代码转换"""
    collector = AKShareFundamentalsCollector({})

    # 上证
    assert collector._convert_stock_code_ak("600000.SH") == "sh600000"
    # 深证
    assert collector._convert_stock_code_ak("000001.SZ") == "sz000001"
    # 北交所
    assert collector._convert_stock_code_ak("831370.BJ") == "bj831370"


def test_rate_limit_check():
    """测试请求频率限制"""
    collector = AKShareFundamentalsCollector({"rate_limit": 2})

    # 前两次请求不应该等待
    collector._rate_limit_check()
    assert collector.request_count == 1
    collector._rate_limit_check()
    assert collector.request_count == 2

    # 验证方法执行正常
    collector._rate_limit_check()
    # 通过即成功


@patch("akshare.stock_info_a_code_name")
def test_get_stock_basic(mock_stock_info_a_code_name):
    """测试获取股票基本信息"""
    mock_data = pd.DataFrame(
        {
            "code": ["000001", "600000"],
            "name": ["平安银行", "浦发银行"],
        }
    )
    mock_stock_info_a_code_name.return_value = mock_data

    collector = AKShareFundamentalsCollector({})
    result = collector.get_stock_basic(list_status="L")

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "ts_code" in result.columns
    assert "name" in result.columns
    # 检查代码转换
    assert "000001.SZ" in result["stock_code"].values
    assert "600000.SH" in result["stock_code"].values


@patch("akshare.stock_info_a_code_name")
def test_get_stock_basic_empty(mock_stock_info_a_code_name):
    """测试获取股票列表返回空"""
    mock_stock_info_a_code_name.return_value = pd.DataFrame()

    collector = AKShareFundamentalsCollector({})
    result = collector.get_stock_basic(list_status="L")

    assert result.empty


@patch("akshare.stock_zh_a_daily")
def test_get_daily_basic(mock_stock_zh_a_daily):
    """测试获取每日基本面"""
    mock_data = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "total_share": [19405652231.0, 19405652231.0],
            "outstanding_share": [19405652231.0, 19405652231.0],
            "total_mv": [200000000000.0, 205000000000.0],
            "close": [10.5, 10.8],
            "turnover": [0.8, 0.9],
        }
    )
    mock_data.set_index("date", inplace=True)
    mock_stock_zh_a_daily.return_value = mock_data

    collector = AKShareFundamentalsCollector({})
    result = collector.get_daily_basic(["000001.SZ"], "2025-01-01", "2025-01-02")

    assert not result.empty
    assert len(result) == 2
    assert "stock_code" in result.columns
    assert "trade_date" in result.columns
    assert "total_mv" in result.columns
    assert "turnover_rate" in result.columns  # 检查重命名
    assert pd.api.types.is_datetime64_dtype(result["trade_date"])


@patch("akshare.stock_zh_a_daily")
def test_get_daily_basic_all_fail(mock_stock_zh_a_daily):
    """测试所有股票都失败返回空"""
    mock_stock_zh_a_daily.return_value = pd.DataFrame()

    collector = AKShareFundamentalsCollector({})
    result = collector.get_daily_basic(["000001.SZ", "600000.SH"], "2025-01-01", "2025-01-02")

    assert result.empty


def test_get_financial_report_unsupported_type():
    """测试不支持的财务报告类型返回空"""
    with patch("akshare.stock_profit_sheet_by_report_em"):
        collector = AKShareFundamentalsCollector({})
        result = collector.get_financial_report(["000001.SZ"], "unknown_type")
        assert result.empty


@patch("akshare.stock_profit_sheet_by_report_em")
def test_get_financial_report_income(mock_financial_report_income):
    """测试获取利润表"""
    mock_data = pd.DataFrame(
        {
            "report_date": ["20241231"],
            "revenue": [100000000],
            "net_profit": [10000000],
        }
    )
    mock_financial_report_income.return_value = mock_data

    collector = AKShareFundamentalsCollector({})
    result = collector.get_financial_report(["000001.SZ"], "income")

    assert not result.empty
    assert "stock_code" in result.columns
    assert "report_type" in result.columns
    assert result["report_type"].iloc[0] == "income"


@patch("akshare.stock_profit_sheet_by_report_em")
def test_get_financial_report_empty(mock_financial_report_income):
    """测试财务报告返回空"""
    mock_financial_report_income.return_value = pd.DataFrame()

    collector = AKShareFundamentalsCollector({})
    result = collector.get_financial_report(["000001.SZ"], "income")

    assert result.empty


@patch("akshare.stock_financial_analysis_indicator")
def test_get_financial_indicator(mock_stock_financial_analysis_indicator):
    """测试获取财务指标"""
    mock_data = pd.DataFrame(
        {
            "date": ["2024-12-31"],
            "净资产收益率": [15.5],
            "总资产净利润率": [0.8],
            "销售毛利率": [35.0],
            "销售净利率": [15.0],
            "资产负债率": [92.0],
            "流动比率": [0.9],
            "速动比率": [0.8],
            "每股收益": [1.5],
            "每股净资产": [12.5],
        }
    )
    mock_stock_financial_analysis_indicator.return_value = mock_data

    collector = AKShareFundamentalsCollector({})
    result = collector.get_financial_indicator(["000001.SZ"], "2024-01-01", "2024-12-31")

    assert not result.empty
    assert "stock_code" in result.columns
    assert "end_date" in result.columns
    assert "roe" in result.columns  # 检查中文重命名
    assert "roa" in result.columns
    assert "gross_margin" in result.columns
    assert "net_margin" in result.columns
    assert "debt_ratio" in result.columns


@patch("akshare.stock_history_dividend")
def test_get_dividend(mock_stock_dividend):
    """测试获取分红数据"""
    mock_data = pd.DataFrame(
        {
            "ex_dividend_date": ["2024-05-16"],
            "record_date": ["2024-05-17"],
            "pay_date": ["2024-05-20"],
            "cash_dividend": [0.25],
            "stock_dividend": [0],
        }
    )
    mock_stock_dividend.return_value = mock_data

    collector = AKShareFundamentalsCollector({})
    result = collector.get_dividend(["000001.SZ"])

    assert not result.empty
    assert "stock_code" in result.columns
    assert "ex_date" in result.columns
    assert "dividend_per_share" in result.columns  # 检查重命名
    assert "bonus_ratio" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["ex_date"])


@patch("akshare.stock_margin_szse")
@patch("akshare.stock_margin_sse")
def test_get_margin_trading(mock_sse, mock_szse):
    """测试获取融资融券数据"""
    mock_data_sse = pd.DataFrame(
        {"信用交易日期": ["20250101", "20250102"], "融资余额": [100000000, 101000000], "融券余量": [50000000, 51000000]}
    )
    mock_data_szse = pd.DataFrame(
        {"信用交易日期": ["20250101", "20250102"], "融资余额": [50000000, 51000000], "融券余量": [25000000, 26000000]}
    )
    mock_sse.return_value = mock_data_sse
    mock_szse.return_value = mock_data_szse

    collector = AKShareFundamentalsCollector({})
    result = collector.get_margin_trading([], "2025-01-01", "2025-01-02")

    assert not result.empty
    assert "trade_date" in result.columns
    assert "margin_balance" in result.columns  # 检查重命名
    assert "short_balance" in result.columns
    assert pd.api.types.is_datetime64_dtype(result["trade_date"])


@patch("akshare.stock_margin_szse")
@patch("akshare.stock_margin_sse")
def test_get_margin_trading_empty(mock_sse, mock_szse):
    """测试融资融券返回空"""
    mock_sse.return_value = pd.DataFrame()
    mock_szse.return_value = pd.DataFrame()

    collector = AKShareFundamentalsCollector({})
    result = collector.get_margin_trading([], "2025-01-01", "2025-01-02")

    assert result.empty


def test_get_source_info():
    """测试获取数据源信息"""
    collector = AKShareFundamentalsCollector({"priority": 5, "weight": 2.0})
    info = collector.get_source_info()

    assert info["source"] == "akshare"
    assert info["priority"] == 5
    assert info["weight"] == 2.0
    assert "availability" in info
    assert "avg_response_time" in info
    assert "error_count" in info
    assert "is_available" in info


def test_validate_data():
    """测试数据校验"""
    collector = AKShareFundamentalsCollector({})

    # 空数据应该无效
    df_empty = pd.DataFrame()
    assert not collector.validate_data(df_empty)

    # 缺少必要字段应该无效
    df_missing = pd.DataFrame({"wrong_column": [1, 2, 3]})
    assert not collector.validate_data(df_missing, required_columns=["stock_code"])

    # 有效数据应该通过
    df_valid = pd.DataFrame({"stock_code": ["000001.SZ", "600000.SH"]})
    assert collector.validate_data(df_valid, required_columns=["stock_code"])
