"""
Unit tests for clickhouse_storage.py
"""

from datetime import date, datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from common.exceptions import StorageException
from data_management.data_storage.clickhouse_storage import ClickHouseStorage


class TestClickHouseStorage:
    """测试ClickHouse存储实现"""

    def test_init_default(self):
        """测试默认初始化"""
        config = {}
        storage = ClickHouseStorage(config)
        assert storage.host == "localhost"
        assert storage.port == 9000
        assert storage.database == "default"
        assert storage.user == "default"
        assert storage.password == ""
        assert storage.chunk_size == 10000

    def test_init_custom(self):
        """测试自定义配置初始化"""
        config = {
            "host": "clickhouse.example.com",
            "port": 9001,
            "database": "stock",
            "user": "admin",
            "password": "secret",
            "chunk_size": 50000,
        }
        storage = ClickHouseStorage(config)
        assert storage.host == "clickhouse.example.com"
        assert storage.port == 9001
        assert storage.database == "stock"
        assert storage.user == "admin"
        assert storage.password == "secret"
        assert storage.chunk_size == 50000

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_connect_success(self, mock_client_cls):
        """测试连接成功"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage(
            {
                "host": "localhost",
                "port": 9000,
                "database": "default",
            }
        )
        result = storage.connect()

        assert result is True
        assert storage.is_connected
        assert storage.connection is mock_client
        mock_client.execute.assert_called_once_with("SELECT 1")
        mock_client_cls.assert_called_once()

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_connect_failure_raises_exception(self, mock_client_cls):
        """测试连接失败抛出异常"""
        mock_client = Mock()
        mock_client.execute.side_effect = ConnectionError("Connection refused")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        with pytest.raises(StorageException, match="ClickHouse连接失败"):
            storage.connect()
        assert not storage.is_connected

    def test_disconnect_success_when_connected(self):
        """测试断开连接成功"""
        storage = ClickHouseStorage({})
        mock_client = Mock()
        storage.connection = mock_client
        storage.is_connected = True

        result = storage.disconnect()

        assert result is True
        assert not storage.is_connected
        mock_client.disconnect.assert_called_once()

    def test_disconnect_no_connection_returns_true(self):
        """测试断开连接当没有连接时"""
        storage = ClickHouseStorage({})
        storage.connection = None
        storage.is_connected = False

        result = storage.disconnect()

        assert result is True
        assert not storage.is_connected

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_disconnect_throws_exception_returns_false(self, mock_client_cls):
        """测试断开连接抛出异常时返回False"""
        mock_client = Mock()
        mock_client.disconnect.side_effect = Exception("Disconnect failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.connect()
        result = storage.disconnect()

        assert result is False

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_write_empty_data_returns_zero(self, mock_client_cls):
        """测试写入空数据返回0"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        df = pd.DataFrame()
        result = storage.write("test_table", df)

        assert result == 0
        mock_client.execute.assert_not_called()

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_write_dataframe_single_chunk(self, mock_client_cls):
        """测试写入DataFrame单块"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({"chunk_size": 10000})
        storage.is_connected = True
        storage.connection = mock_client

        df = pd.DataFrame(
            {
                "col1": [1, 2, 3, 4, 5],
                "col2": ["a", "b", "c", "d", "e"],
            }
        )
        result = storage.write("test_table", df)

        assert result == 5
        assert mock_client.execute.called
        # INSERT called once
        assert mock_client.execute.call_count == 1

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_write_list_dict_converts_to_df(self, mock_client_cls):
        """测试写入字典列表会转换为DataFrame"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        data = [
            {"col1": 1, "col2": "a"},
            {"col1": 2, "col2": "b"},
        ]
        result = storage.write("test_table", data)

        assert result == 2
        assert mock_client.execute.called

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_write_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试写入异常抛出StorageException"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Write failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        df = pd.DataFrame({"col1": [1, 2, 3]})
        with pytest.raises(StorageException, match="ClickHouse写入失败"):
            storage.write("test_table", df)

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_no_query_returns_all(self, mock_client_cls):
        """测试无查询条件返回全部数据"""
        mock_client = Mock()
        # Mock execute result: (rows, column_types)
        mock_client.execute.return_value = (
            [(1, "a"), (2, "b")],
            [("col1", "UInt32"), ("col2", "String")],
        )
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        df = storage.read("test_table")

        assert len(df) == 2
        assert list(df.columns) == ["col1", "col2"]
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args
        assert "SELECT * FROM test_table" in call_args[0][0]

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_with_equality_condition(self, mock_client_cls):
        """测试带等值查询条件"""
        mock_client = Mock()
        mock_client.execute.return_value = ([], [])
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        query = {"trade_date": "2024-01-01"}
        df = storage.read("test_table", query)

        assert df.empty
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "WHERE trade_date = '2024-01-01'" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_with_in_condition(self, mock_client_cls):
        """测试IN查询条件"""
        mock_client = Mock()
        mock_client.execute.return_value = ([], [])
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        query = {"stock_code": ["000001.SZ", "600000.SH"]}
        df = storage.read("test_table", query)

        assert df.empty
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "IN ('000001.SZ', '600000.SH')" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_with_date_range_condition(self, mock_client_cls):
        """测试日期范围查询条件"""
        mock_client = Mock()
        mock_client.execute.return_value = ([], [])
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        query = {"trade_date": (start, end)}
        df = storage.read("test_table", query)

        assert df.empty
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "trade_date >= '2024-01-01' AND trade_date <= '2024-01-31'" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_with_date_object_range(self, mock_client_cls):
        """测试date对象范围查询"""
        mock_client = Mock()
        mock_client.execute.return_value = ([], [])
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        query = {"trade_date": (start, end)}
        df = storage.read("test_table", query)

        assert df.empty
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "trade_date >= '2024-01-01' AND trade_date <= '2024-01-31'" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_with_order_by_and_limit(self, mock_client_cls):
        """测试排序和限制"""
        mock_client = Mock()
        mock_client.execute.return_value = ([], [])
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        df = storage.read("test_table", None, order_by=["-trade_date", "stock_code"], limit=100, offset=10)

        assert df.empty
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "ORDER BY trade_date DESC, stock_code ASC" in sql
        assert "LIMIT 100" in sql
        assert "OFFSET 10" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_converts_datetime_columns(self, mock_client_cls):
        """测试自动转换日期时间列"""
        mock_client = Mock()
        mock_client.execute.return_value = (
            [(1, "2024-01-01"), (2, "2024-01-02")],
            [("id", "UInt32"), ("trade_date", "Date")],
        )
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        df = storage.read("test_table")

        assert pd.api.types.is_datetime64_dtype(df["trade_date"])

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_read_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试查询异常抛出StorageException"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Query failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        with pytest.raises(StorageException, match="ClickHouse查询失败"):
            storage.read("test_table")

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_delete_returns_one(self, mock_client_cls):
        """测试删除返回1"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.delete("test_table", {"id": 1})

        assert result == 1
        mock_client.execute.assert_called_once()

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_delete_with_multiple_conditions(self, mock_client_cls):
        """测试带多个条件的删除"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.delete("test_table", {"trade_date": "2024-01-01", "symbol": "000001.SZ"})

        assert result == 1
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "ALTER TABLE test_table DELETE" in sql
        assert "WHERE" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_delete_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试删除异常抛出StorageException"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Delete failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        with pytest.raises(StorageException, match="ClickHouse删除失败"):
            storage.delete("test_table", {"id": 1})

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_execute_sql_select_returns_df(self, mock_client_cls):
        """测试执行SELECT返回DataFrame"""
        mock_client = Mock()
        mock_client.execute.return_value = (
            [(1, "a"), (2, "b")],
            [("id", "Int32"), ("name", "String")],
        )
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.execute_sql("SELECT id, name FROM test_table")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["id", "name"]

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_execute_sql_non_select_returns_raw_result(self, mock_client_cls):
        """测试执行非SELECT返回原始结果"""
        mock_client = Mock()
        mock_client.execute.return_value = [[1]]
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.execute_sql("CREATE TABLE test (id Int32)")

        assert result == [[1]]

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_execute_sql_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试执行SQL异常抛出StorageException"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("SQL failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        with pytest.raises(StorageException, match="ClickHouse执行SQL失败"):
            storage.execute_sql("SELECT * FROM invalid")

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_table_exists_returns_true(self, mock_client_cls):
        """测试检查表存在返回True"""
        mock_client = Mock()
        mock_client.execute.return_value = [[1]]
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.table_exists("test_table")

        assert result is True
        mock_client.execute.assert_called_once_with("EXISTS TABLE test_table")

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_table_exists_returns_false(self, mock_client_cls):
        """测试表不存在返回False"""
        mock_client = Mock()
        mock_client.execute.return_value = [[0]]
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.table_exists("not_exists")

        assert result is False

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_table_exists_exception_returns_false(self, mock_client_cls):
        """检查表存在时异常返回False"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Error")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.table_exists("test")

        assert result is False

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_create_table_basic(self, mock_client_cls):
        """测试创建基础表"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        schema = {
            "trade_date": "Date",
            "stock_code": "String",
            "close": "Float32",
        }
        result = storage.create_table("test_table", schema, engine="MergeTree", order_by="trade_date")

        assert result is True
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_table" in sql
        assert "trade_date Date" in sql
        assert "stock_code String" in sql
        assert "close Float32" in sql
        assert "ENGINE = MergeTree" in sql
        assert "ORDER BY trade_date" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_create_table_with_partition(self, mock_client_cls):
        """测试创建分区表"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        schema = {"trade_date": "Date", "stock_code": "String", "close": "Float32"}
        result = storage.create_table(
            "test_table",
            schema,
            engine="ReplacingMergeTree",
            partition_by="toYYYYMM(trade_date)",
            order_by="(trade_date, stock_code)",
        )

        assert result is True
        call_args = mock_client.execute.call_args
        sql = call_args[0][0]
        assert "PARTITION BY toYYYYMM(trade_date)" in sql

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_create_table_throws_exception_raises_storage_exception(self, mock_client_cls):
        """测试创建表异常抛出StorageException"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Create failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage({})
        storage.is_connected = True
        storage.connection = mock_client

        with pytest.raises(StorageException, match="ClickHouse创建表失败"):
            storage.create_table("test_table", {})

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_health_check_healthy(self, mock_client_cls):
        """测试健康检查健康状态"""
        mock_client = Mock()
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage(
            {
                "host": "localhost",
                "port": 9000,
                "database": "stock",
            }
        )
        storage.is_connected = True
        storage.connection = mock_client

        result = storage.health_check()

        assert result["status"] == "healthy"
        assert result["host"] == "localhost"
        assert result["port"] == 9000
        assert result["database"] == "stock"
        assert result["is_connected"] is True
        assert "response_time" in result

    @patch("data_management.data_storage.clickhouse_storage.Client")
    def test_health_check_unhealthy(self, mock_client_cls):
        """测试健康检查不健康状态"""
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Connection failed")
        mock_client_cls.return_value = mock_client

        storage = ClickHouseStorage(
            {
                "host": "badhost",
                "port": 9000,
                "database": "default",
            }
        )
        storage.is_connected = False

        result = storage.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["is_connected"] is False
