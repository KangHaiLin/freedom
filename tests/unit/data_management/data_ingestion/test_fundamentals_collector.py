"""
Unit tests for fundamentals_collector.py
"""
import pytest
import pandas as pd
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.data_management.data_ingestion.fundamentals_collector import FundamentalsCollector


class MockFundamentalsCollector(FundamentalsCollector):
    """Mock implementation for testing abstract base class"""

    def get_stock_basic(self, list_status: str = 'L') -> pd.DataFrame:
        return pd.DataFrame()

    def get_daily_basic(self, stock_codes: list, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_financial_report(self, stock_codes: list, report_type: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_financial_indicator(self, stock_codes: list, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()

    def get_dividend(self, stock_codes: list) -> pd.DataFrame:
        return pd.DataFrame()

    def get_margin_trading(self, stock_codes: list, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame()


def test_initialization():
    """测试基类初始化"""
    config = {'priority': 10, 'weight': 2.0, 'max_retry_times': 5, 'retry_interval': 2}
    collector = MockFundamentalsCollector("test_source", config)

    assert collector.source == "test_source"
    assert collector.config == config
    assert collector.priority == 10
    assert collector.weight == 2.0
    assert collector.availability == 1.0
    assert collector.max_retry_times == 5
    assert collector.retry_interval == 2
    assert collector.error_count == 0
    assert collector.last_sync_time is None
    assert collector.last_error_time is None


def test_validate_data_empty():
    """测试空数据校验"""
    collector = MockFundamentalsCollector("test", {})

    df = pd.DataFrame()
    assert collector.validate_data(df) is False


def test_validate_data_missing_column():
    """测试缺少必要字段"""
    collector = MockFundamentalsCollector("test", {})

    df = pd.DataFrame({'wrong_column': [1, 2, 3]})
    assert collector.validate_data(df, required_columns=['stock_code']) is False


def test_validate_data_valid():
    """测试有效数据校验通过"""
    collector = MockFundamentalsCollector("test", {})

    df = pd.DataFrame({'stock_code': ['000001.SZ', '600000.SH'], 'name': ['平安银行', '浦发银行']})
    assert collector.validate_data(df, required_columns=['stock_code', 'name']) is True


def test_record_success():
    """测试成功记录"""
    collector = MockFundamentalsCollector("test", {})
    collector.error_count = 3
    collector.availability = 0.5

    collector.record_success(100.0)

    assert collector.error_count == 2
    assert collector.availability > 0.5  # 可用性应该提升
    assert collector.last_sync_time is not None


def test_record_error():
    """测试错误记录"""
    collector = MockFundamentalsCollector("test", {})
    collector.availability = 1.0

    collector.record_error("test error")

    assert collector.error_count == 1
    assert collector.availability < 1.0  # 可用性应该下降
    assert collector.last_error_time is not None


def test_is_available_when_healthy():
    """测试健康状态下应该可用"""
    collector = MockFundamentalsCollector("test", {})
    assert collector.is_available() is True


def test_is_available_when_unhealthy():
    """测试连续错误后应该不可用"""
    collector = MockFundamentalsCollector("test", {})

    # 连续5次错误
    for _ in range(5):
        collector.record_error()

    # 5分钟内不可用
    assert collector.is_available() is False


def test_is_available_after_cooldown():
    """测试冷却后恢复可用"""
    collector = MockFundamentalsCollector("test", {})

    for _ in range(5):
        collector.record_error()

    # 修改最后错误时间到6分钟前
    collector.last_error_time = time.time() - 360

    # 可用性还是0，因为多次错误后没有成功记录
    assert collector.is_available() is False

    # 记录几次成功后可用性恢复
    for _ in range(5):
        collector.record_success(100.0)

    # 现在应该可用了
    assert collector.is_available() is True


def test_get_source_info():
    """测试获取数据源信息"""
    collector = MockFundamentalsCollector("test_source", {'priority': 5})
    info = collector.get_source_info()

    assert info['source'] == "test_source"
    assert info['priority'] == 5
    assert 'availability' in info
    assert 'avg_response_time' in info
    assert 'error_count' in info
    assert 'is_available' in info


def test_execute_with_retry_success():
    """测试带重试执行成功"""
    collector = MockFundamentalsCollector("test", {'max_retry_times': 3})
    mock_func = Mock(return_value=pd.DataFrame({'test': [1, 2, 3]}))

    result = collector.execute_with_retry(mock_func)

    assert not result.empty
    assert mock_func.call_count == 1


def test_execute_with_retry_failure():
    """测试重试全部失败应该抛出异常"""
    collector = MockFundamentalsCollector("test", {'max_retry_times': 3})
    mock_func = Mock(side_effect=Exception("test error"))

    with pytest.raises(Exception):
        collector.execute_with_retry(mock_func)

    assert mock_func.call_count == 3
