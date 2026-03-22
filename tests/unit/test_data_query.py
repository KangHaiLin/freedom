"""
数据查询模块单元测试
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from data_management.data_query.base_query import QueryCondition, QueryResult
from data_management.data_query.fundamental_data_query import FundamentalDataQuery
from data_management.data_query.market_data_query import MarketDataQuery
from data_management.data_query.query_manager import QueryManager


class TestQueryCondition:
    """查询条件测试"""

    def test_condition_creation(self):
        """测试查询条件创建"""
        condition = QueryCondition()
        condition.filters = {"stock_code": "000001.SZ"}
        condition.start_date = datetime(2023, 1, 1)
        condition.end_date = datetime(2023, 1, 2)
        condition.limit = 100
        condition.stock_codes = ["000001.SZ"]

        assert condition.filters["stock_code"] == "000001.SZ"
        assert condition.limit == 100
        assert condition.stock_codes == ["000001.SZ"]

    def test_to_dict(self):
        """测试转换为字典"""
        condition = QueryCondition()
        condition.filters = {"stock_code": ["000001.SZ", "600000.SH"]}
        condition.limit = 10
        condition.stock_codes = ["000001.SZ", "600000.SH"]

        condition_dict = condition.to_dict()
        assert len(condition_dict["filters"]["stock_code"]) == 2
        assert condition_dict["limit"] == 10


class TestQueryResult:
    """查询结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        result = QueryResult(data=df, total=1, success=True, message="", query_time=0.1)
        assert result.success
        assert not result.to_df().empty
        assert result.query_time == 0.1
        assert result.message == ""

    def test_error_result(self):
        """测试错误结果"""
        result = QueryResult(data=[], total=0, success=False, message="查询失败", query_time=0.05)
        assert not result.success
        assert len(result.data) == 0
        assert result.message == "查询失败"


class TestMarketDataQuery:
    """行情数据查询服务测试"""

    def test_get_realtime_quote(self):
        """测试获取实时行情"""
        mock_df = pd.DataFrame(
            {"stock_code": ["000001.SZ", "600000.SH"], "price": [10.0, 15.0], "time": [datetime.now(), datetime.now()]}
        )

        # 模拟postgresql存储（实时行情存在postgresql）
        mock_postgresql = Mock()
        mock_postgresql.read.return_value = mock_df

        # 模拟其他存储
        mock_clickhouse = Mock()
        mock_redis = Mock()
        mock_redis.read.return_value = None  # 缓存未命中

        # 先设置mock，再创建MarketDataQuery（因为__init__会立即调用get_storage_by_type）
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }[type_name]

        market_query = MarketDataQuery(storage_manager)
        result = market_query.get_realtime_quote(["000001.SZ", "600000.SH"])
        assert result.success
        assert not result.to_df().empty
        assert len(result.to_dict()["data"]) == 2
        assert mock_postgresql.read.called

    def test_get_daily_quote_with_date_range(self):
        """测试获取指定日期范围的日线行情"""
        mock_df = pd.DataFrame(
            {"trade_date": pd.date_range("2023-01-01", "2023-01-10"), "close": [10.0 + i * 0.1 for i in range(10)]}
        )

        mock_redis = Mock()
        mock_redis.read.return_value = None  # 缓存未命中
        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        mock_postgresql = Mock()

        # 先设置mock，再创建MarketDataQuery
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_storage,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }[type_name]

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        market_query = MarketDataQuery(storage_manager)
        result = market_query.get_daily_quote(["000001.SZ"], start_date=start_date, end_date=end_date)
        assert result.success
        df = result.to_df()
        assert not df.empty
        assert len(df) == 10

    def test_calculate_ma(self):
        """测试计算均线"""
        mock_df = pd.DataFrame({"trade_date": pd.date_range("2023-01-01", "2023-01-10"), "close": [10.0] * 10})

        mock_redis = Mock()
        mock_redis.read.return_value = None  # 缓存未命中
        mock_storage = Mock()
        mock_storage.read.return_value = mock_df
        mock_postgresql = Mock()

        # 先设置mock，再创建MarketDataQuery
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_storage,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }[type_name]

        market_query = MarketDataQuery(storage_manager)
        result = market_query.calculate_ma("000001.SZ", periods=[5], days=10)
        assert result.success
        df = result.to_df()
        assert "ma5" in df.columns
        assert df["ma5"].iloc[-1] == 10.0

    def test_query_cache(self):
        """测试查询缓存"""
        mock_redis_storage = Mock()
        mock_redis_storage.read.return_value = None  # 缓存未命中
        mock_postgresql = Mock(read=Mock(return_value=pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})))
        mock_clickhouse = Mock()

        # 先设置mock，再创建MarketDataQuery
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis_storage,
        }[type_name]

        from unittest.mock import patch

        market_query = MarketDataQuery(storage_manager)
        with patch.object(market_query, "_build_cache_key") as mock_cache_key:
            mock_cache_key.return_value = "cache:realtime:000001.SZ"

            # 第一次查询，缓存未命中
            result1 = market_query.get_realtime_quote(["000001.SZ"])

            # 模拟缓存命中 - Redis返回的是JSON字符串，MarketDataQuery会用pd.DataFrame(cache_result)构造
            import json

            mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
            mock_redis_storage.read.return_value = mock_df.to_dict("records")

            # 第二次查询，缓存命中
            result2 = market_query.get_realtime_quote(["000001.SZ"])

            assert result1.success
            assert result2.success


class TestFundamentalDataQuery:
    """基本面数据查询服务测试"""

    def test_get_income_statement(self):
        """测试获取利润表"""
        mock_df = pd.DataFrame(
            {
                "report_date": ["2023-03-31", "2023-06-30"],
                "revenue": [100000000, 150000000],
                "net_profit": [50000000, 75000000],
            }
        )

        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = mock_df
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_redis.read.return_value = None  # 缓存未命中

        # 先设置mock，再创建FundamentalDataQuery
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }[type_name]

        fundamental_query = FundamentalDataQuery(storage_manager)
        result = fundamental_query.get_income_statement(["000001.SZ"], report_type="quarterly")
        assert result.success
        df = result.to_df()
        assert not df.empty
        assert len(df) == 2
        # 降序排列，最新的（150000000）在第一个
        assert df["revenue"].iloc[0] == 150000000
        assert df["revenue"].iloc[1] == 100000000

    def test_get_financial_indicator(self):
        """测试获取财务指标"""
        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "pe": [10.5], "pb": [1.2], "roe": [15.3]})

        mock_clickhouse = Mock()
        mock_clickhouse.read.return_value = mock_df
        mock_postgresql = Mock()
        mock_redis = Mock()
        mock_redis.read.return_value = None  # 缓存未命中

        # 先设置mock，再创建FundamentalDataQuery
        storage_manager = Mock()
        storage_manager.get_storage_by_type.side_effect = lambda type_name: {
            "clickhouse": mock_clickhouse,
            "postgresql": mock_postgresql,
            "redis": mock_redis,
        }[type_name]

        fundamental_query = FundamentalDataQuery(storage_manager)
        result = fundamental_query.get_financial_indicator(["000001.SZ"])
        assert result.success
        df = result.to_df()
        assert not df.empty
        assert df["pe"].iloc[0] == 10.5
        assert df["roe"].iloc[0] == 15.3


class TestQueryManager:
    """查询管理器测试"""

    @patch.dict(
        "common.config.settings.QUERY_CONFIG",
        {
            "default_storage": "postgresql",
            "cache_enabled": True,
            "slow_query_threshold": 1.0,
            "max_query_limit": 100000,
            "query_timeout": 30,
        },
    )
    def test_batch_query(self):
        """测试批量查询"""
        mock_storage = Mock()
        mock_df = pd.DataFrame({"stock_code": ["000001.SZ"], "price": [10.0]})
        mock_storage.read.return_value = mock_df

        # patch 模块级别的全局 storage_manager
        from data_management.data_query import query_manager

        original_sm = query_manager.storage_manager
        query_manager.storage_manager = Mock()
        query_manager.storage_manager.get_storage_by_type = Mock(return_value=mock_storage)
        query_manager.storage_manager.get_storage.return_value = mock_storage

        manager = QueryManager()

        # 创建批量查询 - batch_query接收字典参数列表，不是QueryCondition列表
        queries = [
            {"service_type": "market", "stock_codes": ["000001.SZ"], "filters": {"data_type": "realtime"}},
            {"service_type": "market", "stock_codes": ["600000.SH"], "filters": {"data_type": "daily"}},
        ]

        results = manager.batch_query(queries)
        # 恢复原模块
        query_manager.storage_manager = original_sm

        assert len(results) == 2
        assert all([isinstance(r, QueryResult) for r in results])

    @patch.dict(
        "common.config.settings.QUERY_CONFIG",
        {
            "default_storage": "postgresql",
            "cache_enabled": True,
            "slow_query_threshold": 1.0,
            "max_query_limit": 100000,
            "query_timeout": 30,
        },
    )
    def test_slow_query_monitoring(self):
        """测试慢查询监控"""
        # 这个测试验证慢查询会被记录日志，我们mock掉实际查询只模拟耗时

        # patch 模块级别的全局 storage_manager
        from data_management.data_query import query_manager
        from data_management.data_query.query_manager import QueryManager

        original_sm = query_manager.storage_manager

        # mock整个storage_manager避免实际连接数据库
        mock_sm = Mock()
        mock_sm.health_check = Mock(return_value={"status": "healthy"})
        query_manager.storage_manager = mock_sm

        manager = QueryManager()

        # mock MarketDataQuery.query，模拟一个慢查询（让查询本身耗时 > 5秒会触发警告）
        with patch.object(manager, "get_query_service") as mock_get_service:
            mock_service = Mock()

            def slow_query(*args, **kwargs):
                import time

                time.sleep(0.006)  # 让实际执行时间超过0.005秒？不，阈值是5秒...我们需要看代码
                # QueryManager警告发生在 result.query_time > 5，我们直接mock time.time来让它认为超过5秒
                return QueryResult(data=pd.DataFrame({"stock_code": ["000001.SZ"]}), total=1, success=True)

            mock_service.query = slow_query
            mock_get_service.return_value = mock_service

            import logging
            import time

            query_logger = logging.getLogger("data_management.data_query.query_manager")
            # mock time.time让它模拟一个超过5秒的查询
            start = time.time()
            with patch("time.time") as mock_time:
                mock_time.side_effect = [start, start + 6]  # start 到 end相差6秒
                with patch.object(query_logger, "warning") as mock_warning:
                    result = manager.query(
                        service_type="market", stock_codes=["000001.SZ"], filters={"data_type": "realtime"}
                    )
                    # 恢复原模块
                    query_manager.storage_manager = original_sm
                    assert result.success
                    # 因为耗时6秒超过5秒，应该记录警告
                    mock_warning.assert_called_once()
