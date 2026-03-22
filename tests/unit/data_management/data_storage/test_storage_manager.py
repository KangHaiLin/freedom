"""
Unit tests for storage_manager.py
"""
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from common.exceptions import StorageException
from data_management.data_storage.storage_manager import StorageManager
from data_management.data_storage.base_storage import BaseStorage


class TestStorageManager:
    """测试存储管理器"""

    def test_init_loads_configs(self):
        """测试初始化加载配置"""
        mock_configs = {
            "clickhouse": {
                "type": "clickhouse",
                "host": "localhost",
                "port": 9000,
                "database": "default",
                "default": True,
            },
            "redis": {
                "type": "redis",
                "host": "localhost",
                "port": 6379,
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            with patch('data_management.data_storage.redis_storage.RedisStorage.connect') as mock_connect_redis:
                mock_connect_redis.return_value = True
                manager = StorageManager()
                # Override configs after creation to avoid patching pydantic
                manager.storages = {}
                manager.default_storage = None
                manager.storage_configs = mock_configs
                manager._load_configs()

                assert "clickhouse" in manager.storages
                assert "redis" in manager.storages
                assert manager.default_storage == "clickhouse"

    def test_load_configs_skips_missing_type(self):
        """测试跳过缺少type的配置"""
        mock_configs = {
            "invalid": {
                "host": "localhost",
                "port": 5432,
            },
            "valid": {
                "type": "postgresql",
                "host": "localhost",
            },
        }
        with patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect') as mock_connect:
            mock_connect.return_value = True
            manager = StorageManager()
            # Override configs after creation
            manager.storages = {}
            manager.default_storage = None
            manager.storage_configs = mock_configs
            manager._load_configs()

            assert "invalid" not in manager.storages
            assert "valid" in manager.storages

    def test_load_configs_no_default_uses_first(self):
        """测试没有配置默认存储时使用第一个"""
        mock_configs = {
            "first": {
                "type": "clickhouse",
                "host": "localhost",
            },
            "second": {
                "type": "redis",
                "host": "localhost",
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            with patch('data_management.data_storage.redis_storage.RedisStorage.connect') as mock_connect_redis:
                mock_connect_redis.return_value = True
                manager = StorageManager()
                # Override configs after creation
                manager.storages = {}
                manager.default_storage = None
                manager.storage_configs = mock_configs
                manager._load_configs()

                assert manager.default_storage == "first"

    def test_create_storage_unsupported_type_raises_exception(self):
        """测试不支持的存储类型抛出异常"""
        mock_configs = {}
        manager = StorageManager()
        manager.storage_configs = mock_configs
        manager.storages = {}
        with pytest.raises(StorageException, match="不支持的存储类型"):
            manager._create_storage("mysql", {})

    def test_get_storage_default_returns_default(self):
        """测试获取默认存储"""
        mock_configs = {
            "clickhouse": {
                "type": "clickhouse",
                "default": True,
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            manager = StorageManager()
            manager.storages = {}
            manager.default_storage = None
            manager.storage_configs = mock_configs
            manager._load_configs()
            storage = manager.get_storage()

            assert storage is manager.storages["clickhouse"]

    def test_get_storage_named_returns_correct(self):
        """测试获取命名存储"""
        mock_configs = {
            "clickhouse": {
                "type": "clickhouse",
                "default": True,
            },
            "redis": {
                "type": "redis",
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect_ch:
            mock_connect_ch.return_value = True
            with patch('data_management.data_storage.redis_storage.RedisStorage.connect') as mock_connect_rd:
                mock_connect_rd.return_value = True
                manager = StorageManager()
                manager.storages = {}
                manager.default_storage = None
                manager.storage_configs = mock_configs
                manager._load_configs()
                storage = manager.get_storage("redis")

                assert storage is manager.storages["redis"]

    def test_get_storage_not_exists_raises_exception(self):
        """测试存储不存在抛出异常"""
        mock_configs = {
            "clickhouse": {
                "type": "clickhouse",
                "default": True,
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            manager = StorageManager()
            manager.storages = {}
            manager.default_storage = None
            manager.storage_configs = mock_configs
            manager._load_configs()
            with pytest.raises(StorageException, match="存储实例不存在"):
                manager.get_storage("not_exists")

    def test_get_storage_no_storages_raises_exception(self):
        """测试没有存储抛出异常"""
        mock_configs = {}
        manager = StorageManager()
        manager.storages = {}
        manager.default_storage = None
        manager.storage_configs = mock_configs
        manager._load_configs()
        with pytest.raises(StorageException, match="无可用存储实例"):
            manager.get_storage()

    def test_write_delegates_to_storage(self):
        """测试write委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        mock_storage.write.return_value = 5
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = manager.write("test_table", df)

        assert result == 5
        mock_storage.write.assert_called_once_with("test_table", df)

    def test_read_delegates_to_storage(self):
        """测试read委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        expected_df = pd.DataFrame({"col1": [1, 2, 3]})
        mock_storage.read.return_value = expected_df
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        result = manager.read("test_table", {"id": 1})

        pd.testing.assert_frame_equal(result, expected_df)
        mock_storage.read.assert_called_once_with("test_table", {"id": 1})

    def test_delete_delegates_to_storage(self):
        """测试delete委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        mock_storage.delete.return_value = 3
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        result = manager.delete("test_table", {"id": 1})

        assert result == 3
        mock_storage.delete.assert_called_once_with("test_table", {"id": 1})

    def test_execute_sql_delegates_to_storage(self):
        """测试execute_sql委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        mock_storage.execute_sql.return_value = [[1]]
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        result = manager.execute_sql("SELECT * FROM test")

        assert result == [[1]]
        mock_storage.execute_sql.assert_called_once_with("SELECT * FROM test")

    def test_table_exists_delegates_to_storage(self):
        """测试table_exists委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        mock_storage.table_exists.return_value = True
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        result = manager.table_exists("test_table")

        assert result is True
        mock_storage.table_exists.assert_called_once_with("test_table")

    def test_create_table_delegates_to_storage(self):
        """测试create_table委托给存储"""
        manager = StorageManager()
        manager.storages = {}
        mock_storage = Mock()
        mock_storage.create_table.return_value = True
        manager.storages["default"] = mock_storage
        manager.default_storage = "default"

        schema = {"id": "SERIAL", "name": "VARCHAR"}
        result = manager.create_table("test_table", schema)

        assert result is True
        mock_storage.create_table.assert_called_once_with("test_table", schema)

    def test_health_check_all_storages(self):
        """测试所有存储健康检查"""
        manager = StorageManager()
        mock_storage1 = Mock()
        mock_storage1.health_check.return_value = {"status": "healthy"}
        mock_storage2 = Mock()
        mock_storage2.health_check.return_value = {"status": "unhealthy", "error": "Connection failed"}
        manager.storages = {
            "storage1": mock_storage1,
            "storage2": mock_storage2,
        }
        manager.default_storage = "storage1"

        result = manager.health_check()

        assert result["total_storages"] == 2
        assert result["healthy_storages"] == 1
        assert "storage1" in result["storages"]
        assert "storage2" in result["storages"]
        assert result["health_score"] == 0.5

    def test_health_check_handles_exception(self):
        """测试健康检查处理异常"""
        manager = StorageManager()
        mock_storage = Mock()
        mock_storage.health_check.side_effect = Exception("Unexpected error")
        manager.storages = {"storage": mock_storage}

        result = manager.health_check()

        assert result["storages"]["storage"]["status"] == "unhealthy"
        assert "error" in result["storages"]["storage"]

    def test_connect_all_success(self):
        """测试所有连接成功"""
        manager = StorageManager()
        mock_storage1 = Mock()
        mock_storage1.connect.return_value = True
        mock_storage2 = Mock()
        mock_storage2.connect.return_value = True
        manager.storages = {"s1": mock_storage1, "s2": mock_storage2}

        result = manager.connect_all()

        assert result is True
        mock_storage1.connect.assert_called_once()
        mock_storage2.connect.assert_called_once()

    def test_connect_all_partial_failure_returns_false(self):
        """测试部分连接失败返回False"""
        manager = StorageManager()
        mock_storage1 = Mock()
        mock_storage1.connect.return_value = True
        mock_storage2 = Mock()
        mock_storage1.connect.side_effect = Exception("Connection failed")
        manager.storages = {"s1": mock_storage1, "s2": mock_storage2}

        result = manager.connect_all()

        assert result is False

    def test_disconnect_all_success(self):
        """测试所有断开成功"""
        manager = StorageManager()
        mock_storage1 = Mock()
        mock_storage1.disconnect.return_value = True
        mock_storage2 = Mock()
        mock_storage2.disconnect.return_value = True
        manager.storages = {"s1": mock_storage1, "s2": mock_storage2}

        result = manager.disconnect_all()

        assert result is True

    def test_disconnect_all_partial_failure_returns_false(self):
        """测试部分断开失败返回False"""
        manager = StorageManager()
        mock_storage1 = Mock()
        mock_storage1.disconnect.return_value = True
        mock_storage2 = Mock()
        mock_storage2.disconnect.side_effect = Exception("Disconnect failed")
        manager.storages = {"s1": mock_storage1, "s2": mock_storage2}

        result = manager.disconnect_all()

        assert result is False

    def test_get_storage_by_type_found_returns_first(self):
        """测试按类型找到返回第一个"""
        mock_configs = {
            "clickhouse1": {
                "type": "clickhouse",
            },
            "clickhouse2": {
                "type": "clickhouse",
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            manager = StorageManager()
            manager.storages = {}
            manager.default_storage = None
            manager.storage_configs = mock_configs
            manager._load_configs()

            result = manager.get_storage_by_type("clickhouse")

            assert result is manager.storages["clickhouse1"]

    def test_get_storage_by_type_not_found_returns_none(self):
        """测试按类型找不到返回None"""
        mock_configs = {
            "clickhouse": {
                "type": "clickhouse",
            },
        }
        with patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect') as mock_connect:
            mock_connect.return_value = True
            manager = StorageManager()
            manager.storages = {}
            manager.default_storage = None
            manager.storage_configs = mock_configs
            manager._load_configs()

            result = manager.get_storage_by_type("mysql")

            assert result is None

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        from data_management.data_storage.storage_manager import storage_manager
        assert storage_manager is not None
        assert isinstance(storage_manager, StorageManager)
