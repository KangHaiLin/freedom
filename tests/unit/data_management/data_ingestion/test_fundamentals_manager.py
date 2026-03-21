"""
Unit tests for fundamentals_manager.py
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch

from src.data_management.data_ingestion.fundamentals_manager import FundamentalsManager
from src.data_management.data_ingestion.fundamentals_collector import FundamentalsCollector
from common.exceptions import DataSourceException


class MockCollector:
    """Mock collector for testing"""

    def __init__(self, source_name, available=True, should_fail=False):
        self.source = source_name
        self.priority = 10
        self.weight = 1.0
        self.availability = 1.0 if available else 0.0
        self.avg_response_time = 100.0
        self.error_count = 0

        self.is_available = Mock(return_value=available)
        self.get_source_info = Mock(return_value={
            'source': source_name,
            'priority': self.priority,
            'availability': self.availability,
            'is_available': available,
        })

        if not should_fail:
            self.get_stock_basic = Mock(return_value=pd.DataFrame({
                'stock_code': ['000001.SZ', '600000.SH'],
                'name': ['平安银行', '浦发银行']
            }))
            self.get_daily_basic = Mock(return_value=pd.DataFrame({
                'stock_code': ['000001.SZ'],
                'trade_date': pd.to_datetime(['2025-01-01']),
                'pe': [10.5],
                'pb': [1.2]
            }))
        else:
            self.get_stock_basic = Mock(return_value=pd.DataFrame())
            self.get_daily_basic = Mock(return_value=pd.DataFrame())


def test_initialization():
    """测试管理器初始化"""
    manager = FundamentalsManager()
    assert len(manager.sources) == 0
    assert len(manager.source_map) == 0


def test_add_source():
    """测试添加数据源"""
    manager = FundamentalsManager()
    collector = MockCollector("tushare")

    manager.add_source(collector)

    assert len(manager.sources) == 1
    assert "tushare" in manager.source_map
    assert manager.get_source_by_name("tushare") == collector


def test_remove_source():
    """测试移除数据源"""
    manager = FundamentalsManager()
    collector = MockCollector("tushare")
    manager.add_source(collector)

    manager.remove_source("tushare")

    assert len(manager.sources) == 0
    assert "tushare" not in manager.source_map


def test_get_available_source_count():
    """测试获取可用数据源数量"""
    manager = FundamentalsManager()
    manager.add_source(MockCollector("tushare", available=True))
    manager.add_source(MockCollector("wind", available=False))

    assert manager.get_available_source_count() == 1


def test_select_best_source():
    """测试选择最优数据源"""
    import random
    # 固定随机种子确保测试可重复
    random.seed(42)

    manager = FundamentalsManager()
    tushare = MockCollector("tushare", available=True)
    wind = MockCollector("wind", available=True)
    wind.priority = 5  # 更高优先级（数字更小）
    wind.weight = 10.0  # 给予更高权重确保选中
    manager.add_source(tushare)
    manager.add_source(wind)

    selected = manager.select_best_source()

    # 优先级更高的应该被选中
    assert selected.source == "wind"


def test_execute_query_success():
    """测试执行查询成功"""
    manager = FundamentalsManager()
    manager.add_source(MockCollector("tushare", available=True))

    result = manager.execute_query('get_stock_basic', 'L')

    assert not result.empty
    assert len(result) == 2


def test_execute_query_all_fail():
    """测试所有数据源都失败应该抛出异常"""
    manager = FundamentalsManager()
    manager.add_source(MockCollector("tushare", available=True, should_fail=True))
    manager.add_source(MockCollector("wind", available=True, should_fail=True))

    with pytest.raises(DataSourceException):
        manager.execute_query('get_stock_basic', 'L')


def test_execute_query_no_available():
    """测试没有可用数据源应该抛出异常"""
    manager = FundamentalsManager()
    manager.add_source(MockCollector("tushare", available=False))

    with pytest.raises(DataSourceException):
        manager.execute_query('get_stock_basic', 'L')


def test_convenience_methods():
    """测试便捷方法封装"""
    manager = FundamentalsManager()
    collector = MockCollector("tushare", available=True)
    collector.get_financial_indicator = Mock(return_value=pd.DataFrame({
        'stock_code': ['000001.SZ'],
        'end_date': pd.to_datetime(['2024-12-31']),
        'roe': [15.5]
    }))
    manager.add_source(collector)

    # 测试各个便捷方法
    result = manager.get_stock_basic('L')
    assert not result.empty

    result = manager.get_daily_basic(['000001.SZ'], '2025-01-01', '2025-12-31')
    assert not result.empty

    result = manager.get_financial_indicator(['000001.SZ'], '2025-01-01', '2025-12-31')
    assert not result.empty

    # 验证mock被调用
    collector.get_financial_indicator.assert_called_once()


def test_health_check():
    """测试健康检查"""
    manager = FundamentalsManager()
    manager.add_source(MockCollector("tushare", available=True))
    manager.add_source(MockCollector("wind", available=False))

    health = manager.health_check()

    assert health['total_sources'] == 2
    assert health['available_sources'] == 1
    assert health['health_score'] == 0.5
    assert len(health['sources']) == 2
    assert 'check_time' in health
