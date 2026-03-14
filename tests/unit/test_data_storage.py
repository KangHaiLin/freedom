"""
数据存储模块单元测试
"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from data_management.data_storage.postgresql_storage import PostgreSQLStorage
from data_management.data_storage.clickhouse_storage import ClickHouseStorage
from data_management.data_storage.redis_storage import RedisStorage
from data_management.data_storage.storage_manager import StorageManager


class TestPostgreSQLStorage:
    """PostgreSQL存储测试"""

    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_connect(self, mock_create_engine, mock_connect):
        """测试连接"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test',
            'user': 'test',
            'password': 'test'
        }
        storage = PostgreSQLStorage(config)
        storage.connect()
        assert storage.is_connected
        mock_connect.assert_called_once()
        mock_create_engine.assert_called_once()

    def test_write(self):
        """测试写入数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()

        # 测试DataFrame写入
        data = pd.DataFrame({
            'stock_code': ['000001.SZ', '600000.SH'],
            'price': [10.0, 15.0],
            'time': [datetime.now(), datetime.now()]
        })

        with patch.object(pd.DataFrame, 'to_sql') as mock_to_sql:
            rows_written = storage.write('test_table', data)
            assert rows_written == 2
            mock_to_sql.assert_called_once()

    def test_read(self):
        """测试查询数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()

        mock_df = pd.DataFrame({'stock_code': ['000001.SZ'], 'price': [10.0]})
        with patch('pandas.read_sql', return_value=mock_df):
            result = storage.read('test_table', {'stock_code': '000001.SZ'})
            assert not result.empty
            assert len(result) == 1


class TestRedisStorage:
    """Redis存储测试"""

    @patch('redis.Redis')
    def test_connect(self, mock_redis):
        """测试连接"""
        config = {'host': 'localhost', 'port': 6379, 'db': 0}
        storage = RedisStorage(config)
        mock_redis.return_value.ping.return_value = True
        storage.connect()
        assert storage.is_connected
        mock_redis.assert_called_once()

    def test_write_read(self):
        """测试写入和读取数据"""
        config = {'host': 'localhost', 'port': 6379, 'db': 0}
        storage = RedisStorage(config)
        storage.connection = Mock()
        storage.connection.get.return_value = '{"key": "value"}'

        # 测试写入字典
        data = {'key': 'value'}
        rows_written = storage.write('test', data, key='test_key')
        assert rows_written == 1
        storage.connection.setex.assert_called_once()

        # 测试读取
        result = storage.read('test', {'key': 'test_key'})
        assert result == {'key': 'value'}


class TestStorageManager:
    """存储管理器测试"""

    @patch.dict('common.config.settings.STORAGE_CONFIGS', {
        'redis': {
            'type': 'redis',
            'host': 'localhost',
            'default': True
        },
        'postgresql': {
            'type': 'postgresql',
            'host': 'localhost',
            'database': 'test',
            'user': 'test',
            'password': 'test'
        }
    })
    def test_init(self):
        """测试初始化"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'):
            manager = StorageManager()
            assert len(manager.storages) == 2
            assert manager.default_storage == 'redis'

    def test_get_storage(self):
        """测试获取存储实例"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch.dict('common.config.settings.STORAGE_CONFIGS', {
                'redis': {'type': 'redis', 'host': 'localhost', 'default': True},
                'postgresql': {'type': 'postgresql', 'host': 'localhost'}
             }):
            manager = StorageManager()
            redis_storage = manager.get_storage('redis')
            assert redis_storage is not None
            assert redis_storage.__class__.__name__ == 'RedisStorage'

            default_storage = manager.get_storage()
            assert default_storage == redis_storage
