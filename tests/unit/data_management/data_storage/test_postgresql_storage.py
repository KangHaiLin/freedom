"""
Unit tests for postgresql_storage.py
"""

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from common.exceptions import StorageException
from data_management.data_storage.postgresql_storage import PostgreSQLStorage


class TestPostgreSQLStorage:
    """测试PostgreSQL存储实现"""

    def test_init(self):
        """测试初始化"""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "stock",
            "user": "postgres",
            "password": "postgres",
            "schema": "stock",
            "chunk_size": 2000,
        }
        storage = PostgreSQLStorage(config)
        assert storage.host == "localhost"
        assert storage.port == 5432
        assert storage.database == "stock"
        assert storage.user == "postgres"
        assert storage.password == "postgres"
        assert storage.schema == "stock"
        assert storage.chunk_size == 2000
        assert "postgresql://postgres:postgres@localhost:5432/stock" in storage.conn_str

    def test_init_default_schema(self):
        """测试默认schema"""
        config = {
            "database": "stock",
            "user": "postgres",
            "password": "postgres",
        }
        storage = PostgreSQLStorage(config)
        assert storage.schema == "public"
        assert storage.chunk_size == 1000

    @patch("data_management.data_storage.postgresql_storage.psycopg2.connect")
    @patch("data_management.data_storage.postgresql_storage.create_engine")
    def test_connect_success(self, mock_create_engine, mock_connect):
        """测试连接成功"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        config = {
            "host": "localhost",
            "port": 5432,
            "database": "stock",
            "user": "postgres",
            "password": "postgres",
        }
        storage = PostgreSQLStorage(config)
        result = storage.connect()

        assert result is True
        assert storage.is_connected
        assert storage.connection is mock_conn
        assert storage.engine is mock_engine
        mock_connect.assert_called_once()
        mock_create_engine.assert_called_once()
        assert mock_conn.autocommit is True

    @patch("data_management.data_storage.postgresql_storage.psycopg2.connect")
    def test_connect_failure_raises_exception(self, mock_connect):
        """测试连接失败抛出异常"""
        mock_connect.side_effect = Exception("Connection refused")

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        with pytest.raises(StorageException, match="PostgreSQL连接失败"):
            storage.connect()
        assert not storage.is_connected

    @patch("data_management.data_storage.postgresql_storage.psycopg2.connect")
    @patch("data_management.data_storage.postgresql_storage.create_engine")
    def test_disconnect_success(self, mock_create_engine, mock_connect):
        """测试断开连接成功"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.connect()
        result = storage.disconnect()

        assert result is True
        assert not storage.is_connected
        mock_conn.close.assert_called_once()
        mock_engine.dispose.assert_called_once()

    @patch("data_management.data_storage.postgresql_storage.psycopg2.connect")
    @patch("data_management.data_storage.postgresql_storage.create_engine")
    def test_disconnect_throws_exception_returns_false(self, mock_create_engine, mock_connect):
        """测试断开连接异常返回False"""
        mock_conn = Mock()
        mock_conn.close.side_effect = Exception("Close failed")
        mock_connect.return_value = mock_conn
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.connect()
        result = storage.disconnect()

        assert result is False

    def test_write_empty_data_returns_zero(self):
        """测试写入空数据返回0"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        df = pd.DataFrame()
        result = storage.write("test_table", df)

        assert result == 0

    @patch("pandas.DataFrame.to_sql")
    def test_write_small_data_uses_to_sql(self, mock_to_sql):
        """测试小数据量使用to_sql"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()
        storage.schema = "public"

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        result = storage.write("test_table", df)

        assert result == 3
        mock_to_sql.assert_called_once()

    def test_write_list_dict_converts_to_df(self):
        """测试写入字典列表转换为DataFrame"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
            data = [{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]
            result = storage.write("test_table", data)

            assert result == 2
            mock_to_sql.assert_called_once()

    @patch("data_management.data_storage.postgresql_storage.execute_values")
    def test_write_large_data_uses_execute_values(self, mock_execute_values):
        """测试大数据量使用execute_values"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.schema = "public"

        mock_cursor = Mock()
        mock_cursor.rowcount = 1500
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn
        storage.engine = Mock()

        # Create large DataFrame to trigger batch path
        df = pd.DataFrame({"col1": list(range(1500)), "col2": list(range(1500))})
        result = storage.write("test_table", df, if_exists="replace")

        assert result == 1500
        mock_execute_values.assert_called_once()

    def test_write_throws_exception_raises_storage_exception(self):
        """测试写入异常抛出StorageException"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        df = pd.DataFrame({"col1": [1, 2, 3]})
        with patch.object(df, "to_sql") as mock_to_sql:
            mock_to_sql.side_effect = Exception("Write failed")
            with pytest.raises(StorageException, match="PostgreSQL写入失败"):
                storage.write("test_table", df)

    @patch("pandas.read_sql")
    def test_read_no_query_returns_all(self, mock_read_sql):
        """测试无查询条件返回全部"""
        mock_read_sql.return_value = pd.DataFrame({"col1": [1, 2, 3]})

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()
        storage.schema = "public"

        df = storage.read("test_table")

        assert len(df) == 3
        call_args = mock_read_sql.call_args
        assert "SELECT * FROM public.test_table" in call_args[0][0]

    @patch("pandas.read_sql")
    def test_read_with_query_conditions(self, mock_read_sql):
        """测试带查询条件"""
        mock_read_sql.return_value = pd.DataFrame()

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        query = {
            "id": [1, 2, 3],
            "status": "active",
            "price": (10, 100),
        }
        df = storage.read("test_table", query)

        assert df.empty
        call_args = mock_read_sql.call_args
        sql = call_args[0][0]
        assert "WHERE id IN (%s, %s, %s)" in sql
        assert "status = %s" in sql
        assert "price >= %s AND price <= %s" in sql

    @patch("pandas.read_sql")
    def test_read_with_order_by_limit_offset(self, mock_read_sql):
        """测试带排序分页"""
        mock_read_sql.return_value = pd.DataFrame()

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        df = storage.read("test_table", None, order_by=["-id", "name"], limit=10, offset=20)

        assert df.empty
        call_args = mock_read_sql.call_args
        sql = call_args[0][0]
        assert "ORDER BY id DESC, name ASC" in sql
        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql

    def test_read_throws_exception_raises_storage_exception(self):
        """测试查询异常抛出StorageException"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        with patch("pandas.read_sql") as mock_read_sql:
            mock_read_sql.side_effect = Exception("Query failed")
            with pytest.raises(StorageException, match="PostgreSQL查询失败"):
                storage.read("test_table")

    def test_delete_returns_deleted_count(self):
        """测试删除返回删除行数"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.schema = "public"

        mock_cursor = Mock()
        mock_cursor.rowcount = 5
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.delete("test_table", {"id": 1})

        assert result == 5
        mock_cursor.execute.assert_called_once()

    def test_delete_with_multiple_conditions(self):
        """测试多条件删除"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.schema = "public"

        mock_cursor = Mock()
        mock_cursor.rowcount = 3
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.delete("test_table", {"status": "inactive", "id": [1, 2, 3]})

        assert result == 3
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "DELETE FROM public.test_table" in sql
        assert "WHERE" in sql

    def test_delete_throws_exception_raises_storage_exception(self):
        """测试删除异常抛出StorageException"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Delete failed")
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        with pytest.raises(StorageException, match="PostgreSQL删除失败"):
            storage.delete("test_table", {"id": 1})

    @patch("pandas.read_sql")
    def test_execute_sql_select_returns_df(self, mock_read_sql):
        """测试执行SELECT返回DataFrame"""
        mock_read_sql.return_value = pd.DataFrame({"id": [1, 2, 3]})

        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        result = storage.execute_sql("SELECT * FROM test_table")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_execute_sql_non_select_returns_rowcount(self):
        """测试执行非SELECT返回行数"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.rowcount = 10
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.execute_sql("DELETE FROM test_table WHERE id < 10")

        assert result == 10

    def test_execute_sql_throws_exception_raises_storage_exception(self):
        """测试执行SQL异常抛出StorageException"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("SQL failed")
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        with pytest.raises(StorageException, match="PostgreSQL执行SQL失败"):
            storage.execute_sql("DELETE FROM test_table WHERE id < 10")

    def test_table_exists_returns_true(self):
        """测试表存在返回True"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.schema = "public"

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [True]
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.table_exists("test_table")

        assert result is True
        mock_cursor.execute.assert_called_once()

    def test_table_exists_returns_false(self):
        """测试表不存在返回False"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [False]
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.table_exists("not_exists")

        assert result is False

    def test_table_exists_exception_returns_false(self):
        """检查表存在异常返回False"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Error")
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.table_exists("test_table")

        assert result is False

    def test_create_table_with_single_primary_key(self):
        """测试创建表带单主键"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.schema = "public"

        mock_cursor = Mock()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        schema = {
            "id": "SERIAL PRIMARY KEY",
            "name": "VARCHAR(100)",
            "price": "NUMERIC(10,2)",
        }
        result = storage.create_table("test_table", schema)

        assert result is True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS public.test_table" in sql
        assert "id SERIAL PRIMARY KEY" in sql

    def test_create_table_with_composite_primary_key(self):
        """测试创建表带复合主键"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        schema = {
            "trade_date": "DATE",
            "stock_code": "VARCHAR(10)",
            "close": "NUMERIC(10,2)",
        }
        result = storage.create_table("test_table", schema, primary_key=["trade_date", "stock_code"])

        assert result is True
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "PRIMARY KEY (trade_date, stock_code)" in sql

    def test_create_table_throws_exception_raises_storage_exception(self):
        """测试创建表异常抛出StorageException"""
        config = {"database": "stock", "user": "postgres", "password": "postgres"}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Create failed")
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        with pytest.raises(StorageException, match="PostgreSQL创建表失败"):
            storage.create_table("test_table", {})

    def test_health_check_healthy(self):
        """测试健康检查健康状态"""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "stock",
            "user": "postgres",
            "password": "postgres",
        }
        storage = PostgreSQLStorage(config)
        storage.is_connected = True

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor_context
        storage.connection = mock_conn

        result = storage.health_check()

        assert result["status"] == "healthy"
        assert result["host"] == "localhost"
        assert result["is_connected"] is True

    def test_health_check_unhealthy(self):
        """测试健康检查不健康状态"""
        config = {
            "host": "badhost",
            "port": 5432,
            "database": "stock",
            "user": "postgres",
            "password": "postgres",
        }
        storage = PostgreSQLStorage(config)
        storage.is_connected = False

        with patch("psycopg2.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            result = storage.health_check()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert result["is_connected"] is False
