"""
数据流程集成测试
测试完整数据流：数据采集 → 数据清洗 → 数据存储 → 数据查询 → API接口
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from data_management.data_ingestion.data_cleaner import DataCleaner
from data_management.data_ingestion.tushare_collector import TushareCollector
from data_management.data_query.query_manager import QueryManager
from data_management.data_storage.storage_manager import StorageManager


class TestFullDataFlow:
    """完整数据流程集成测试"""

    def test_full_realtime_data_flow(self, sample_realtime_data):
        """测试实时行情完整数据流"""
        # 1. 数据采集阶段
        with patch("tushare.pro_api") as mock_tushare_api:
            collector = TushareCollector({"api_key": "test_key", "priority": 1, "weight": 1.0})

            # 模拟采集返回数据
            mock_pro = Mock()
            mock_pro.realtime_quote.return_value = sample_realtime_data
            mock_tushare_api.return_value = mock_pro

            collected_data = collector.get_realtime_quote(["000001.SZ", "600000.SH"])
            assert not collected_data.empty
            assert len(collected_data) == 4

        # 2. 数据清洗阶段
        cleaner = DataCleaner()
        cleaned_data = cleaner.clean_realtime_quote(collected_data)
        assert not cleaned_data.empty
        assert "stock_code" in cleaned_data.columns
        assert "time" in cleaned_data.columns
        assert "price" in cleaned_data.columns

        # 3. 数据存储阶段
        with patch("psycopg2.connect"), patch("sqlalchemy.create_engine"):
            storage_manager = StorageManager()
            mock_storage = Mock()
            mock_storage.write.return_value = len(cleaned_data)
            storage_manager.get_storage.return_value = mock_storage

            rows_written = storage_manager.write("realtime_quotes", cleaned_data)
            assert rows_written == len(cleaned_data)
            mock_storage.write.assert_called_once_with("realtime_quotes", cleaned_data)

        # 4. 数据查询阶段
        query_manager = QueryManager()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = cleaned_data
        query_manager.execute_query.return_value = mock_result

        from data_management.data_query.base_query import QueryCondition

        condition = QueryCondition(
            table_name="realtime_quotes", filters={"stock_code": ["000001.SZ", "600000.SH"]}, limit=100
        )
        query_result = query_manager.execute_query(condition)
        assert query_result.success
        assert not query_result.data.empty
        assert len(query_result.data) == 4

        # 5. API接口阶段
        from user_interface.backend.main import app

        client = TestClient(app)

        # 模拟API返回
        with patch("user_interface.backend.routers.market.query_manager") as mock_query:
            mock_result = Mock()
            mock_result.success = True
            mock_result.data.to_dict.return_value = cleaned_data.to_dict("records")
            mock_query.execute_query.return_value = mock_result

            headers = {"X-API-Key": "test_key"}
            response = client.get("/api/v1/market/realtime?stock_codes=000001.SZ,600000.SH", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]) == 4
            assert any(item["stock_code"] == "000001.SZ" for item in data["data"])

    def test_daily_data_analysis_flow(self, sample_daily_data):
        """测试日线数据分析流程"""
        # 1. 存储日线数据
        with patch("psycopg2.connect"), patch("sqlalchemy.create_engine"):
            storage_manager = StorageManager()
            mock_storage = Mock()
            mock_storage.write.return_value = len(sample_daily_data)
            storage_manager.get_storage.return_value = mock_storage

            rows_written = storage_manager.write("daily_quotes", sample_daily_data)
            assert rows_written == 10

        # 2. 查询并计算均线
        query_manager = QueryManager()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = sample_daily_data
        query_manager.execute_query.return_value = mock_result

        # 模拟均线计算
        from data_management.data_query.market_data_query import MarketDataQuery

        market_query = MarketDataQuery(None)
        data_with_ma = market_query.calculate_ma(sample_daily_data, period=5)
        assert "ma5" in data_with_ma.columns
        # 前4天没有均线值
        assert pd.isna(data_with_ma["ma5"].iloc[0])
        assert not pd.isna(data_with_ma["ma5"].iloc[4])
        # 前5天的均值应该是 (10.1 + 10.2 + 10.3 + 10.4 + 10.5) / 5 = 10.3
        assert round(data_with_ma["ma5"].iloc[4], 2) == 10.3

    def test_data_quality_monitoring_flow(self, sample_realtime_data):
        """测试数据质量监控流程"""
        # 1. 构造有质量问题的数据
        bad_data = sample_realtime_data.copy()
        bad_data.loc[1, "price"] = -1.0  # 无效价格
        bad_data.loc[2, "stock_code"] = None  # 缺失股票代码
        bad_data.loc[3, "time"] = datetime.now().replace(year=2020)  # 过时数据

        # 2. 数据质量检查
        from data_management.data_monitoring.data_quality_monitor import DataQualityMonitor

        monitor = DataQualityMonitor(
            "test_quality",
            storage_manager=None,
            config={
                "table_name": "realtime_quotes",
                "metrics": ["completeness", "accuracy", "timeliness"],
                "thresholds": {"overall_score": 0.8},
            },
        )

        completeness = monitor._check_completeness(bad_data)
        accuracy = monitor._check_accuracy(bad_data)

        assert completeness < 1.0  # 有缺失值
        assert accuracy < 1.0  # 有无效值
        assert completeness + accuracy < 1.9

        # 3. 监控结果告警
        from data_management.data_monitoring.base_monitor import AlertLevel, MonitorResult

        result = MonitorResult.failure(
            "realtime_quality",
            AlertLevel.WARNING,
            metrics={"completeness": completeness, "accuracy": accuracy},
            message="数据质量不达标",
        )

        from data_management.data_monitoring.alert_service import AlertService

        alert_service = AlertService(config={"channels": ["log"]})

        with patch("logging.warning") as mock_log:
            alert_service.send_alert(result, channels=["log"])
            mock_log.assert_called_once()
            assert "数据质量不达标" in str(mock_log.call_args)
