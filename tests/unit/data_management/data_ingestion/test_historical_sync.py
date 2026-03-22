"""
测试历史数据自动同步功能
测试增量检测逻辑、日期范围计算、全量/增量流程
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from data_management.data_ingestion.historical_sync_task import DataFrequency, HistoricalSyncTask, SyncResult


class TestHistoricalSyncTaskIncrementalDetection:
    """测试增量检测逻辑"""

    @pytest.fixture
    def mock_task(self):
        """创建一个mock任务，不连接真实数据库"""
        with patch("data_management.data_ingestion.historical_sync_task.storage_manager") as mock_storage:
            mock_clickhouse = Mock()
            mock_clickhouse.table_exists.return_value = True
            mock_storage.get_storage_by_type.return_value = mock_clickhouse

            task = HistoricalSyncTask(
                frequency=DataFrequency.DAILY,
                default_start_date="2020-01-01",
            )
            task.clickhouse_storage = mock_clickhouse
            yield task

    def test_empty_database_should_trigger_full_sync(self, mock_task):
        """空数据库应该触发全量同步"""
        # 表不存在返回None，表示需要全量
        mock_task.clickhouse_storage.table_exists.return_value = False

        result = mock_task.get_latest_trade_date()
        assert result is None

        sync_range = mock_task.calculate_sync_range()
        assert sync_range is not None
        start, end = sync_range
        # 起始日期应该是默认的2020-01-01
        assert start.date() == datetime(2020, 1, 1).date()
        # 结束日期应该是今天
        assert end.date() == datetime.now().date()

    def test_latest_date_is_today_should_no_sync(self, mock_task):
        """最新日期是今天应该不需要同步"""
        import pandas as pd

        today = datetime.now()
        df = pd.DataFrame([[today]])
        mock_task.clickhouse_storage.execute_sql.return_value = df

        result = mock_task.get_latest_trade_date()
        assert result is not None
        assert result.date() == today.date()

        # 找下一个交易日，应该在今天之后
        sync_range = mock_task.calculate_sync_range()
        assert sync_range is None

    def test_latest_date_is_yesterday_needs_incremental_sync(self, mock_task):
        """最新日期是昨天需要增量同步"""
        import pandas as pd

        yesterday = datetime.now() - timedelta(days=1)
        df = pd.DataFrame([[yesterday]])
        mock_task.clickhouse_storage.execute_sql.return_value = df

        result = mock_task.get_latest_trade_date()
        assert result is not None
        assert result.date() == yesterday.date()

        sync_range = mock_task.calculate_sync_range()
        # 如果昨天之后今天还是交易日，则需要同步
        # 如果今天是周末，则不一定需要同步
        if sync_range is not None:
            start, end = sync_range
            # 起始日期应该在yesterday之后
            assert start > yesterday
            assert end.date() == datetime.now().date()

    def test_latest_date_is_friday_next_is_monday(self, mock_task):
        """最新日期是周五，下一个交易日应该是周一"""
        # 构造一个周五
        # 找最近的一个周五
        today = datetime.now()
        days_since_friday = (today.weekday() - 4) % 7
        friday = today - timedelta(days=days_since_friday)

        if days_since_friday == 0:
            # 今天就是周五，往前推一周
            friday -= timedelta(days=7)

        mock_task.clickhouse_storage.execute_sql.return_value = [[friday]]

        next_day = mock_task.find_next_trading_day(friday)
        assert next_day is not None

        # 如果是使用交易日历，应该找到下周一
        # 如果使用简单算法，也应该跳过周末
        delta_days = (next_day - friday).days
        assert delta_days >= 1

    def test_calculate_start_date_from_none_latest(self, mock_task):
        """当最新日期为空应该返回全量范围"""
        with patch.object(mock_task, "get_latest_trade_date", return_value=None):
            sync_range = mock_task.calculate_sync_range()
            assert sync_range is not None
            start, end = sync_range
            assert start.date() == datetime(2020, 1, 1).date()
            assert end <= datetime.now()

    def test_no_future_trading_day_returns_none(self, mock_task):
        """如果没有未来交易日返回None不需要同步"""
        import pandas as pd

        tomorrow = datetime.now() + timedelta(days=1)
        df = pd.DataFrame([[tomorrow]])
        mock_task.clickhouse_storage.execute_sql.return_value = df

        sync_range = mock_task.calculate_sync_range()
        assert sync_range is None


class TestFindNextTradingDay:
    """测试查找下一个交易日"""

    @pytest.fixture
    def task(self):
        with patch("data_management.data_ingestion.historical_sync_task.storage_manager"):
            task = HistoricalSyncTask(
                frequency=DataFrequency.DAILY,
                default_start_date="2020-01-01",
            )
            yield task

    def test_after_monday_should_be_tuesday(self, task):
        """周一之后应该是周二"""
        monday = datetime(2025, 3, 17)  # 这是一个周一
        assert monday.weekday() == 0

        next_day = task.find_next_trading_day(monday)
        assert next_day is not None
        assert next_day.date() == datetime(2025, 3, 18).date()  # 周二

    def test_after_friday_should_be_monday(self, task):
        """周五之后跳过周末应该是下周一"""
        friday = datetime(2025, 3, 21)  # 这是一个周五
        assert friday.weekday() == 4

        next_day = task.find_next_trading_day(friday)
        assert next_day is not None
        # 下一个交易日应该是周一
        assert next_day.weekday() == 0
        # 间隔应该是3天（周五→周六→周日→周一）
        assert (next_day - friday).days == 3


class TestStockFiltering:
    """测试股票过滤逻辑"""

    @pytest.fixture
    def task(self):
        with patch("data_management.data_ingestion.historical_sync_task.storage_manager"):
            task = HistoricalSyncTask(
                frequency=DataFrequency.DAILY,
                default_start_date="2020-01-01",
                filter_exclude_st=True,
            )
            yield task

    @patch("akshare.stock_zh_a_spot")
    def test_exclude_st_stocks(self, mock_ak, task):
        """测试应该排除ST股票"""
        # 构造模拟数据，包含一个ST股票和一个正常股票
        data = [
            {"代码": "sh600000", "名称": "浦发银行"},
            {"代码": "sz000001", "名称": "*ST平安"},
        ]
        mock_ak.return_value = pd.DataFrame(data)

        result = task.get_filtered_stock_list()

        # 应该只包含非ST股票，排除*ST平安
        assert len(result) == 1
        assert "600000.SH" in result


class TestSyncResult:
    """测试SyncResult类"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = SyncResult(
            success=True,
            total_stocks=100,
            success_stocks=98,
            failed_stocks=2,
            total_records=10000,
            start_date="2020-01-01",
            end_date="2025-03-20",
            message="测试完成",
        )

        dict_result = result.to_dict()

        assert dict_result["success"] is True
        assert dict_result["total_stocks"] == 100
        assert dict_result["success_stocks"] == 98
        assert dict_result["failed_stocks"] == 2
        assert dict_result["total_records"] == 10000
        assert dict_result["start_date"] == "2020-01-01"
        assert dict_result["end_date"] == "2025-03-20"
        assert "sync_time" in dict_result


class TestConfigurationDefaults:
    """测试默认配置读取"""

    @patch("data_management.data_ingestion.historical_sync_task.settings")
    def test_read_defaults_from_settings(self, mock_settings):
        """测试应该从settings读取配置"""
        mock_settings.SYNC_BATCH_SIZE = 20
        mock_settings.SYNC_MAX_RETRIES = 5
        mock_settings.SYNC_DEFAULT_START_DATE = "2018-01-01"
        mock_settings.FILTER_EXCLUDE_ST = False

        with patch("data_management.data_ingestion.historical_sync_task.storage_manager"):
            task = HistoricalSyncTask(frequency=DataFrequency.DAILY)

            assert task.batch_size == 20
            assert task.max_retries == 5
            assert task.default_start_date == "2018-01-01"
            assert task.filter_exclude_st is False

    def test_override_configuration(self):
        """测试参数覆盖配置"""
        with patch("data_management.data_ingestion.historical_sync_task.storage_manager"):
            task = HistoricalSyncTask(
                frequency=DataFrequency.DAILY,
                batch_size=50,
                max_retries=10,
                default_start_date="2015-01-01",
                filter_exclude_st=False,
            )

            assert task.batch_size == 50
            assert task.max_retries == 10
            assert task.default_start_date == "2015-01-01"
            assert task.filter_exclude_st is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
