"""
数据采集模块单元测试
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from data_management.data_ingestion.data_cleaner import DataCleaner
from data_management.data_ingestion.data_source_manager import DataSourceManager
from data_management.data_ingestion.market_collector import MarketDataCollector
from data_management.data_ingestion.tushare_collector import TushareCollector


class TestMarketCollector:
    """行情采集器基类测试"""

    # 创建测试子类
    class TestCollector(MarketDataCollector):
        def get_realtime_quote(self, stock_codes):
            pass

        def get_daily_quote(self, stock_codes, start_date, end_date):
            pass

        def get_minute_quote(self, stock_codes, start_date, end_date, period=1):
            pass

        def get_tick_quote(self, stock_codes, date):
            pass

    def test_record_success(self):
        """测试记录成功请求"""
        config = {"priority": 1, "weight": 1.0}
        collector = self.TestCollector("test_source", config)
        collector.record_success(100.0)
        assert abs(collector.avg_response_time - 30.0) < 0.01  # 滑动平均：0*0.7 + 100*0.3 = 30
        assert abs(collector.availability - 1.0) < 0.01
        assert collector.error_count == 0

    def test_record_error(self):
        """测试记录错误请求"""
        config = {"priority": 1, "weight": 1.0}
        collector = self.TestCollector("test_source", config)
        collector.record_error("test error")
        assert collector.error_count == 1
        assert abs(collector.availability - 0.7) < 0.01

    def test_is_available(self):
        """测试数据源可用性判断"""
        config = {"priority": 1, "weight": 1.0}
        collector = self.TestCollector("test_source", config)
        collector.availability = 0.5
        assert collector.is_available()

        collector.availability = 0.2
        assert not collector.is_available()

        collector.availability = 0.5
        collector.error_count = 5
        collector.last_error_time = datetime.now().timestamp()
        assert not collector.is_available()


class TestDataCleaner:
    """数据清洗器测试"""

    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_clean_realtime_quote(self):
        """测试清洗实时行情数据"""
        # 构造测试数据
        data = [
            {"stock_code": "000001.SZ", "time": "2023-01-01 09:30:00", "price": 10.0, "volume": 1000},
            {"stock_code": "000001.SZ", "time": "2023-01-01 09:30:00", "price": 10.1, "volume": 2000},  # 重复数据
            {"stock_code": "000001.SZ", "time": "2023-01-01 09:31:00", "price": "invalid", "volume": 3000},  # 无效价格
        ]
        df = pd.DataFrame(data)

        cleaned_df = self.cleaner.clean_realtime_quote(df)
        assert len(cleaned_df) == 2  # 去重后2条，无效价格会被转为NaN然后过滤
        assert cleaned_df["stock_code"].iloc[0] == "000001.SZ"

    def test_clean_daily_quote(self):
        """测试清洗日线行情数据"""
        data = [
            {
                "stock_code": "000001.SZ",
                "trade_date": "2023-01-01",
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.2,
                "volume": 100000,
            },
            {
                "stock_code": "000001.SZ",
                "trade_date": "2023-01-02",
                "open": 10.2,
                "high": 9.8,
                "low": 10.5,
                "close": 10.3,
                "volume": 200000,
            },  # 价格不合理
        ]
        df = pd.DataFrame(data)

        cleaned_df = self.cleaner.clean_daily_quote(df)
        assert len(cleaned_df) == 1  # 第二条价格不合理被过滤
        assert float(cleaned_df["close"].iloc[0]) == 10.2

    def test_validate_data_quality(self):
        """测试数据质量校验"""
        from datetime import datetime

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = [
            {"stock_code": "000001.SZ", "time": current_time, "price": 10.0, "volume": 1000},
            {"stock_code": "600000.SH", "time": current_time, "price": 15.0, "volume": 2000},
        ]
        df = pd.DataFrame(data)

        quality_report = self.cleaner.validate_data_quality(df, "realtime")
        assert quality_report["total_count"] == 2
        assert quality_report["valid_count"] == 2
        assert quality_report["quality_score"] >= 0.9
        assert quality_report["status"] == "excellent"


class TestDataSourceManager:
    """数据源管理器测试"""

    def setup_method(self):
        self.manager = DataSourceManager()
        # 创建模拟数据源
        self.source1 = Mock(spec=MarketDataCollector)
        self.source1.source = "source1"
        self.source1.priority = 1
        self.source1.weight = 2.0
        self.source1.availability = 1.0
        self.source1.avg_response_time = 100.0
        self.source1.is_available.return_value = True

        self.source2 = Mock(spec=MarketDataCollector)
        self.source2.source = "source2"
        self.source2.priority = 2
        self.source2.weight = 1.0
        self.source2.availability = 0.8
        self.source2.avg_response_time = 200.0
        self.source2.is_available.return_value = True

    def test_add_source(self):
        """测试添加数据源"""
        self.manager.add_source(self.source1)
        assert len(self.manager.sources) == 1
        assert self.manager.source_map["source1"] == self.source1

    def test_select_best_source(self):
        """测试选择最优数据源"""
        import random

        # 设置随机种子保证测试确定性
        random.seed(42)
        self.manager.add_source(self.source1)
        self.manager.add_source(self.source2)

        best_source = self.manager.select_best_source()
        # 由于是加权随机选择，source1权重更高应该被选中
        assert best_source == self.source1  # source1优先级更高，得分更高

    def test_execute_query(self):
        """测试执行查询"""
        self.manager.add_source(self.source1)
        self.manager.add_source(self.source2)

        # 模拟返回数据
        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        self.source1.get_realtime_quote.return_value = mock_df

        result = self.manager.execute_query("get_realtime_quote", ["000001.SZ"])
        assert not result.empty
        assert len(result) == 1
        self.source1.get_realtime_quote.assert_called_once_with(["000001.SZ"])
