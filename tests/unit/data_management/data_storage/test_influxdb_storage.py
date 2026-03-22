"""
Unit tests for influxdb_storage.py
"""
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest

from common.exceptions import StorageException
from data_management.data_storage.influxdb_storage import InfluxDBStorage
from influxdb_client.client.write_api import SYNCHRONOUS


class TestInfluxDBStorage:
    """测试InfluxDB存储实现"""

    def test_init_default(self):
        """测试默认初始化"""
        config = {
            "token": "test-token",
        }
        storage = InfluxDBStorage(config)
        assert storage.url == "http://localhost:8086"
        assert storage.token == "test-token"
        assert storage.org == "default"
        assert storage.bucket == "default"

    def test_init_custom(self):
        """测试自定义初始化"""
        config = {
            "url": "http://influxdb.example.com:8086",
            "token": "my-token",
            "org": "my-org",
            "bucket": "my-bucket",
            "timeout": 60000,
        }
        storage = InfluxDBStorage(config)
        assert storage.url == "http://influxdb.example.com:8086"
        assert storage.token == "my-token"
        assert storage.org == "my-org"
        assert storage.bucket == "my-bucket"
        assert storage.timeout == 60000

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_connect_success(self, mock_client_cls):
        """测试连接成功"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_health.version = "2.7.0"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_query_api = Mock()
        mock_delete_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.query_api.return_value = mock_query_api
        mock_client.delete_api.return_value = mock_delete_api
        mock_client_cls.return_value = mock_client

        config = {"url": "http://localhost:8086", "token": "test"}
        storage = InfluxDBStorage(config)
        result = storage.connect()

        assert result is True
        assert storage.is_connected
        assert storage.connection is mock_client
        assert storage.write_api is mock_write_api
        assert storage.query_api is mock_query_api
        mock_client.health.assert_called_once()

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_connect_health_check_fails_raises_exception(self, mock_client_cls):
        """测试健康检查失败抛出异常"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "fail"
        mock_health.message = "Service unavailable"
        mock_client.health.return_value = mock_health
        mock_client_cls.return_value = mock_client

        config = {"url": "http://localhost:8086", "token": "test"}
        storage = InfluxDBStorage(config)
        with pytest.raises(StorageException, match="InfluxDB健康检查失败"):
            storage.connect()
        assert not storage.is_connected

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_connect_failure_raises_exception(self, mock_client_cls):
        """测试连接失败抛出异常"""
        mock_client_cls.side_effect = Exception("Connection refused")

        config = {"url": "http://localhost:8086", "token": "test"}
        storage = InfluxDBStorage(config)
        with pytest.raises(StorageException, match="InfluxDB连接失败"):
            storage.connect()

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_disconnect_success(self, mock_client_cls):
        """测试断开连接成功"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()
        result = storage.disconnect()

        assert result is True
        assert not storage.is_connected
        mock_client.close.assert_called_once()

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_disconnect_throws_exception_returns_false(self, mock_client_cls):
        """测试断开连接异常返回False"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_client.close.side_effect = Exception("Close failed")
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()
        result = storage.disconnect()

        assert result is False

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_write_empty_data_returns_zero(self, mock_client_cls):
        """测试写入空数据返回0"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = pd.DataFrame()
        result = storage.write("measurement", df)

        assert result == 0
        mock_write_api.write.assert_not_called()

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_write_no_time_column_raises_exception(self, mock_client_cls):
        """测试没有time列抛出异常"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = pd.DataFrame({"value": [1, 2, 3]})
        with pytest.raises(StorageException, match="InfluxDB写入数据必须包含time字段"):
            storage.write("measurement", df)

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_write_data_with_tags_success(self, mock_client_cls):
        """测试带标签写入成功"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.query_api.return_value = Mock()
        mock_client.delete_api.return_value = Mock()
        mock_client_cls.return_value = mock_client

        config = {"token": "test", "bucket": "test-bucket"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = pd.DataFrame({
            "time": [1620000000000000000, 1620000001000000000],
            "symbol": ["000001.SZ", "600000.SH"],
            "price": [10.5, 20.3],
            "volume": [1000000, 2000000],
        })
        result = storage.write("market_data", df, tags=["symbol"])

        assert result == 2
        mock_write_api.write.assert_called_once()
        call_args = mock_write_api.write.call_args
        assert call_args[1]["bucket"] == "test-bucket"
        assert len(call_args[1]["record"]) == 2

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_write_list_converts_to_df(self, mock_client_cls):
        """测试列表数据转换为DataFrame"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        data = [
            {"time": 1620000000000000000, "value": 10},
            {"time": 1620000001000000000, "value": 20},
        ]
        result = storage.write("measurement", data)

        assert result == 2

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_write_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试写入异常抛出StorageException"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Write failed")
        mock_client.write_api.return_value = mock_write_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = pd.DataFrame({"time": [1, 2, 3], "value": [10, 20, 30]})
        with pytest.raises(StorageException, match="InfluxDB写入失败"):
            storage.write("measurement", df)

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_read_with_default_time_range(self, mock_client_cls):
        """测试默认时间范围查询"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_df = pd.DataFrame({
            "time": ["2024-01-01T00:00:00Z", "2024-01-01T00:01:00Z"],
            "price": [10.5, 10.6],
        })
        mock_query_api.query_data_frame.return_value = mock_df
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test", "bucket": "test-bucket"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = storage.read("market_data")

        assert isinstance(df, pd.DataFrame)
        mock_query_api.query_data_frame.assert_called_once()
        call_args = mock_query_api.query_data_frame.call_args
        flux_query = call_args[0][0]
        assert 'from(bucket: "test-bucket")' in flux_query
        assert 'range(start: -1h, stop: now())' in flux_query
        assert 'r._measurement == "market_data"' in flux_query

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_read_with_tag_filters(self, mock_client_cls):
        """测试带标签过滤查询"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = pd.DataFrame()
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = storage.read("market_data", {"symbol": "000001.SZ"})

        assert df.empty
        call_args = mock_query_api.query_data_frame.call_args
        flux_query = call_args[0][0]
        assert 'r.symbol == "000001.SZ"' in flux_query

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_read_with_list_tag_filter(self, mock_client_cls):
        """测试列表标签过滤查询"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = pd.DataFrame()
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = storage.read("market_data", {"symbol": ["000001.SZ", "600000.SH"]})

        assert df.empty
        call_args = mock_query_api.query_data_frame.call_args
        flux_query = call_args[0][0]
        assert 'r.symbol == "000001.SZ" or r.symbol == "600000.SH"' in flux_query

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_read_with_fields_filter(self, mock_client_cls):
        """测试字段过滤查询"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = pd.DataFrame()
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        df = storage.read("market_data", None, fields=["price", "volume"])

        assert df.empty
        call_args = mock_query_api.query_data_frame.call_args
        flux_query = call_args[0][0]
        assert 'r._field == "price" or r._field == "volume"' in flux_query

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_read_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试查询异常抛出StorageException"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query_data_frame.side_effect = Exception("Query failed")
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        with pytest.raises(StorageException, match="InfluxDB查询失败"):
            storage.read("market_data")

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_delete_returns_one(self, mock_client_cls):
        """测试删除返回1"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_delete_api = Mock()
        mock_client.delete_api.return_value = mock_delete_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test", "bucket": "test-bucket"}
        storage = InfluxDBStorage(config)
        storage.connect()

        result = storage.delete("market_data", {"symbol": "000001.SZ"})

        assert result == 1
        mock_delete_api.delete.assert_called_once()

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_delete_with_multiple_conditions(self, mock_client_cls):
        """测试多条件删除"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_delete_api = Mock()
        mock_client.delete_api.return_value = mock_delete_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        result = storage.delete("market_data", {"symbol": ["000001.SZ", "600000.SH"], "source": "tushare"})

        assert result == 1
        call_args = mock_delete_api.delete.call_args
        predicate = call_args[1]["predicate"]
        assert '_measurement="market_data"' in predicate
        assert 'and (symbol="000001.SZ" or symbol="600000.SH")' in predicate
        assert 'and source="tushare"' in predicate

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_delete_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试删除异常抛出StorageException"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_delete_api = Mock()
        mock_delete_api.delete.side_effect = Exception("Delete failed")
        mock_client.delete_api.return_value = mock_delete_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        with pytest.raises(StorageException, match="InfluxDB删除失败"):
            storage.delete("market_data", {})

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_execute_sql_returns_df(self, mock_client_cls):
        """测试执行原生Flux查询返回DataFrame"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_df = pd.DataFrame({"_time": [1, 2], "_value": [10, 20]})
        mock_query_api.query_data_frame.return_value = mock_df
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        flux_query = 'from(bucket: "default") |> range(start: -1h)'
        result = storage.execute_sql(flux_query)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_execute_sql_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试执行Flux异常抛出StorageException"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query_data_frame.side_effect = Exception("Flux failed")
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        with pytest.raises(StorageException, match="InfluxDB执行Flux失败"):
            storage.execute_sql("invalid flux")

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_table_exists_with_data_returns_true(self, mock_client_cls):
        """测试存在数据返回True"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_result = [Mock()]  # 有数据
        mock_query_api.query.return_value = mock_result
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test", "bucket": "test-bucket"}
        storage = InfluxDBStorage(config)
        storage.connect()

        result = storage.table_exists("market_data")

        assert result is True

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_table_exists_no_data_returns_false(self, mock_client_cls):
        """测试不存在数据返回False"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query.return_value = []
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        result = storage.table_exists("not_exists")

        assert result is False

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_table_exists_exception_returns_false(self, mock_client_cls):
        """测试检查存在异常返回False"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_client.health.return_value = mock_health
        mock_query_api = Mock()
        mock_query_api.query.side_effect = Exception("Error")
        mock_client.query_api.return_value = mock_query_api
        mock_client_cls.return_value = mock_client

        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.connect()

        result = storage.table_exists("market_data")

        assert result is False

    def test_create_table_always_returns_true(self):
        """测试创建表总是返回True"""
        config = {"token": "test"}
        storage = InfluxDBStorage(config)
        storage.is_connected = True
        storage.connection = Mock()

        result = storage.create_table("measurement", {})

        assert result is True

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_health_check_healthy(self, mock_client_cls):
        """测试健康检查健康状态"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "pass"
        mock_health.version = "2.7.0"
        mock_client.health.return_value = mock_health
        mock_client_cls.return_value = mock_client

        config = {
            "url": "http://localhost:8086",
            "token": "test",
            "org": "default",
            "bucket": "default",
        }
        storage = InfluxDBStorage(config)
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.health_check()

        assert result["status"] == "healthy"
        assert result["version"] == "2.7.0"
        assert result["is_connected"] is True

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_health_check_unhealthy(self, mock_client_cls):
        """测试健康检查不健康状态"""
        mock_client = Mock()
        mock_health = Mock()
        mock_health.status = "fail"
        mock_client.health.return_value = mock_health
        mock_client_cls.return_value = mock_client

        config = {
            "url": "http://localhost:8086",
            "token": "test",
            "org": "default",
            "bucket": "default",
        }
        storage = InfluxDBStorage(config)
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.health_check()

        assert result["status"] == "unhealthy"

    @patch('data_management.data_storage.influxdb_storage.InfluxDBClient')
    def test_health_check_throws_exception(self, mock_client_cls):
        """测试健康检查抛出异常"""
        mock_client = Mock()
        mock_client.health.side_effect = Exception("Health check failed")
        mock_client_cls.return_value = mock_client

        config = {
            "url": "http://badhost:8086",
            "token": "test",
            "org": "default",
            "bucket": "default",
        }
        storage = InfluxDBStorage(config)
        storage.is_connected = False

        result = storage.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
