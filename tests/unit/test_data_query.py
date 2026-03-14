"""
数据查询模块单元测试
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from data_management.data_query.market_data_query import MarketDataQuery
from data_management.data_query.fundamental_data_query import FundamentalDataQuery
from data_management.data_query.query_manager import QueryManager
from data_management.data_query.base_query import QueryCondition, QueryResult


class TestQueryCondition:
    """查询条件测试"""

    def test_condition_creation(self):
        """测试查询条件创建"""
        condition = QueryCondition(
            table_name="realtime_quotes",
            filters={"stock_code": "000001.SZ"},
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 1, 2),
            limit=100
        )
        assert condition.table_name == "realtime_quotes"
        assert condition.filters["stock_code"] == "000001.SZ"
        assert condition.limit == 100

    def test_to_dict(self):
        """测试转换为字典"""
        condition = QueryCondition(
            table_name="daily_quotes",
            filters={"stock_code": ["000001.SZ", "600000.SH"]},
            limit=10
        )
        condition_dict = condition.to_dict()
        assert condition_dict["table_name"] == "daily_quotes"
        assert len(condition_dict["filters"]["stock_code"]) == 2


class TestQueryResult:
    """查询结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        result = QueryResult.success(df, query_time=0.1)
        assert result.success
        assert not result.data.empty
        assert result.query_time == 0.1
        assert result.error is None

    def test_error_result(self):
        """测试错误结果"""
        result = QueryResult.error("查询失败", query_time=0.05)
        assert not result.success
        assert result.data is None
        assert result.error == "查询失败"


class TestMarketDataQuery:
    """行情数据查询服务测试"""

    def setup_method(self):
        self.storage_manager = Mock()
        self.market_query = MarketDataQuery(self.storage_manager)

    def test_get_realtime_quote(self):
        """测试获取实时行情"""
        mock_df = pd.DataFrame({
            "stock_code": ["000001.SZ", "600000.SH"],
            "price": [10.0, 15.0],
            "time": [datetime.now(), datetime.now()]
        })

        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        self.storage_manager.get_storage.return_value = mock_storage

        result = self.market_query.get_realtime_quote(["000001.SZ", "600000.SH"])
        assert not result.empty
        assert len(result) == 2
        mock_storage.read.assert_called_once()

    def test_get_daily_quote_with_date_range(self):
        """测试获取指定日期范围的日线行情"""
        mock_df = pd.DataFrame({
            "trade_date": pd.date_range("2023-01-01", "2023-01-10"),
            "close": [10.0 + i * 0.1 for i in range(10)]
        })

        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        self.storage_manager.get_storage.return_value = mock_storage

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        result = self.market_query.get_daily_quote(
            "000001.SZ",
            start_date=start_date,
            end_date=end_date
        )
        assert not result.empty
        assert len(result) == 10

    def test_calculate_ma(self):
        """测试计算均线"""
        data = pd.DataFrame({
            "trade_date": pd.date_range("2023-01-01", "2023-01-10"),
            "close": [10.0] * 10
        })

        result = self.market_query.calculate_ma(data, period=5)
        assert "ma5" in result.columns
        assert result["ma5"].iloc[-1] == 10.0

    @patch.object(MarketDataQuery, '_get_cache_key')
    @patch('redis.Redis.get')
    def test_query_cache(self, mock_redis_get, mock_cache_key):
        """测试查询缓存"""
        mock_cache_key.return_value = "cache:realtime:000001.SZ"
        mock_redis_get.return_value = None  # 缓存未命中

        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        self.storage_manager.get_storage.return_value = mock_storage

        # 第一次查询，缓存未命中
        result1 = self.market_query.get_realtime_quote(["000001.SZ"])

        # 模拟缓存命中
        from io import BytesIO
        buffer = BytesIO()
        mock_df.to_pickle(buffer)
        buffer.seek(0)
        mock_redis_get.return_value = buffer.getvalue()

        # 第二次查询，缓存命中
        result2 = self.market_query.get_realtime_quote(["000001.SZ"])

        assert not result1.empty
        assert not result2.empty
        # 存储只被调用一次（第一次查询）
        mock_storage.read.assert_called_once()


class TestFundamentalDataQuery:
    """基本面数据查询服务测试"""

    def setup_method(self):
        self.storage_manager = Mock()
        self.fundamental_query = FundamentalDataQuery(self.storage_manager)

    def test_get_financial_statement(self):
        """测试获取财务报表"""
        mock_df = pd.DataFrame({
            "report_date": ["2023-03-31", "2023-06-30"],
            "revenue": [100000000, 150000000],
            "net_profit": [50000000, 75000000]
        })

        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        self.storage_manager.get_storage.return_value = mock_storage

        result = self.fundamental_query.get_financial_statement(
            "000001.SZ",
            report_type="quarterly",
            year=2023
        )
        assert not result.empty
        assert len(result) == 2
        assert result["revenue"].iloc[0] == 100000000

    def test_get_financial_indicators(self):
        """测试获取财务指标"""
        mock_df = pd.DataFrame({
            "stock_code": ["000001.SZ"],
            "pe": [10.5],
            "pb": [1.2],
            "roe": [15.3]
        })

        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        self.storage_manager.get_storage.return_value = mock_storage

        result = self.fundamental_query.get_financial_indicators(["000001.SZ"])
        assert not result.empty
        assert result["pe"].iloc[0] == 10.5
        assert result["roe"].iloc[0] == 15.3


class TestQueryManager:
    """查询管理器测试"""

    @patch.dict('common.config.settings.QUERY_CONFIG', {
        "default_storage": "postgresql",
        "cache_enabled": True,
        "slow_query_threshold": 1.0
    })
    def test_batch_query(self):
        """测试批量查询"""
        mock_storage = Mock()
        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        mock_storage.read.return_value = mock_df

        with patch('data_management.data_query.query_manager.StorageManager') as mock_sm_class:
            mock_sm = Mock()
            mock_sm.get_storage.return_value = mock_storage
            mock_sm_class.return_value = mock_sm

            manager = QueryManager()

            # 创建查询条件
            conditions = [
                QueryCondition(
                    table_name="realtime_quotes",
                    filters={"stock_code": "000001.SZ"}
                ),
                QueryCondition(
                    table_name="daily_quotes",
                    filters={"stock_code": "600000.SH"}
                )
            ]

            results = manager.batch_query(conditions)
            assert len(results) == 2
            assert all([isinstance(r, QueryResult) for r in results])
            assert all([r.success for r in results])

    def test_slow_query_monitoring(self):
        """测试慢查询监控"""
        mock_storage = Mock()
        # 模拟查询耗时2秒
        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        def slow_read(*args, **kwargs):
            import time
            time.sleep(0.001)  # 模拟耗时
            return mock_df
        mock_storage.read.side_effect = slow_read

        with patch('data_management.data_query.query_manager.StorageManager') as mock_sm_class:
            mock_sm = Mock()
            mock_sm.get_storage.return_value = mock_storage
            mock_sm_class.return_value = mock_sm

            manager = QueryManager()
            manager.slow_query_threshold = 0.0001  # 设置很低的阈值，让查询变成慢查询

            condition = QueryCondition(
                table_name="realtime_quotes",
                filters={"stock_code": "000001.SZ"}
            )

            with patch.object(manager, '_record_slow_query') as mock_record:
                result = manager.execute_query(condition)
                assert result.success
                mock_record.assert_called_once()  # 慢查询被记录
