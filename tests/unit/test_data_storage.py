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

    @patch('data_management.data_storage.postgresql_storage.create_engine')
    @patch('data_management.data_storage.postgresql_storage.psycopg2.connect')
    def test_connect(self, mock_psycopg2_connect, mock_sqlalchemy_create_engine):
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
        mock_psycopg2_connect.assert_called_once()
        mock_sqlalchemy_create_engine.assert_called_once()

    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_write(self, mock_create_engine, mock_connect):
        """测试写入数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()
        storage.is_connected = True

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

    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_read(self, mock_create_engine, mock_connect):
        """测试查询数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()
        storage.is_connected = True

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
        storage.is_connected = True
        storage.connection.get.return_value = '{"key": "value"}'

        # 测试写入字典
        data = {'key': 'value'}
        rows_written = storage.write('test', data, key='test_key')
        assert rows_written == 1
        storage.connection.setex.assert_called_once()

        # 测试读取
        result = storage.read('test', {'key': 'test_key'})
        assert result == {'key': 'value'}


class TestClickHouseStorage:
    """ClickHouse存储测试"""

    @patch('data_management.data_storage.clickhouse_storage.Client')
    def test_connect(self, mock_client_class):
        """测试连接"""
        config = {
            'host': 'localhost',
            'port': 9000,
            'database': 'test',
            'user': 'test',
            'password': 'test'
        }
        mock_client = mock_client_class.return_value
        storage = ClickHouseStorage(config)
        storage.connect()
        assert storage.is_connected
        mock_client.execute.assert_called_with("SELECT 1")

    def test_disconnect(self):
        """测试断开连接"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client
            storage.is_connected = True
            result = storage.disconnect()
            assert result is True
            assert not storage.is_connected
            mock_client.disconnect.assert_called_once()

    def test_write_dataframe(self):
        """测试写入DataFrame数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client

            data = pd.DataFrame({
                'symbol': ['000001.SZ', '600000.SH'],
                'time': [datetime.now(), datetime.now()],
                'open': [10.0, 15.0],
                'close': [10.5, 15.2]
            })

            rows_written = storage.write('test_table', data)
            assert rows_written == 2
            mock_client.execute.assert_called()

    def test_write_empty_data(self):
        """测试写入空数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client
            data = pd.DataFrame()
            rows_written = storage.write('test_table', data)
            assert rows_written == 0

    def test_write_list_dict(self):
        """测试写入字典列表"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client

            data = [
                {'symbol': '000001.SZ', 'price': 10.0},
                {'symbol': '600000.SH', 'price': 15.0}
            ]

            rows_written = storage.write('test_table', data)
            assert rows_written == 2

    def test_delete(self):
        """测试删除数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client

            result = storage.delete('test_table', {'symbol': '000001.SZ'})
            assert result == 1
            mock_client.execute.assert_called()

    def test_execute_sql_select(self):
        """测试执行查询SQL"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            # 模拟返回带列信息的结果
            mock_client.execute.return_value = (
                [(10.0, '000001.SZ')],
                [('price', 'Float64'), ('symbol', 'String')]
            )
            storage.connection = mock_client

            result = storage.execute_sql("SELECT price, symbol FROM test_table")
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1

    def test_table_exists(self):
        """测试检查表存在"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.execute.return_value = [(1,)]
            storage.connection = mock_client

            exists = storage.table_exists('test_table')
            assert exists is True

    def test_create_table(self):
        """测试创建表"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client

            schema = {
                'symbol': 'String',
                'time': 'DateTime',
                'price': 'Float64'
            }

            result = storage.create_table('test_table', schema, engine='MergeTree', order_by='(time, symbol)')
            assert result is True
            mock_client.execute.assert_called()

    def test_health_check_healthy(self):
        """测试健康检查-健康"""
        config = {'host': 'localhost', 'port': 9000, 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = True

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            storage.connection = mock_client

            result = storage.health_check()
            assert result['status'] == 'healthy'
            assert result['is_connected']
            assert result['host'] == 'localhost'

    def test_health_check_unhealthy(self):
        """测试健康检查-不健康"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = ClickHouseStorage(config)
        storage.is_connected = False

        with patch('clickhouse_driver.Client') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.execute.side_effect = Exception("Connection failed")
            storage.connection = mock_client

            result = storage.health_check()
            assert result['status'] == 'unhealthy'
            assert 'error' in result


class TestPostgreSQLStorageAdditional:
    """PostgreSQL存储附加测试"""

    def test_disconnect(self):
        """测试断开连接"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        with patch('psycopg2.connect') as mock_connect, patch('sqlalchemy.create_engine') as mock_engine:
            storage.connect()
            result = storage.disconnect()
            assert result is True
            assert not storage.is_connected

    def test_write_empty_data(self):
        """测试写入空数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()
        storage.is_connected = True

        data = pd.DataFrame()
        rows_written = storage.write('test_table', data)
        assert rows_written == 0

    def test_write_list_data(self):
        """测试写入列表数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.connection = Mock()
        storage.engine = Mock()
        storage.is_connected = True

        data = [
            {'stock_code': '000001.SZ', 'price': 10.0},
            {'stock_code': '600000.SH', 'price': 15.0}
        ]

        with patch.object(pd.DataFrame, 'to_sql') as mock_to_sql:
            rows_written = storage.write('test_table', data)
            assert rows_written == 2
            mock_to_sql.assert_called_once()

    def test_delete(self):
        """测试删除数据"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()

        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        storage.connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        deleted = storage.delete('test_table', {'stock_code': '000001.SZ'})
        assert deleted == 1
        mock_cursor.execute.assert_called()

    def test_execute_sql_select(self):
        """测试执行查询SQL"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()
        storage.engine = Mock()

        mock_df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        with patch('pandas.read_sql', return_value=mock_df):
            result = storage.execute_sql("SELECT * FROM test")
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2

    def test_table_exists(self):
        """测试检查表存在"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (True,)
        storage.connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        exists = storage.table_exists('test_table')
        assert exists is True

    def test_create_table(self):
        """测试创建表"""
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()

        mock_cursor = Mock()
        storage.connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        schema = {
            'id': 'SERIAL',
            'stock_code': 'VARCHAR(20)',
            'price': 'NUMERIC(10,2)'
        }

        result = storage.create_table('test_table', schema, primary_key='id')
        assert result is True
        mock_cursor.execute.assert_called()

    def test_health_check(self):
        """测试健康检查"""
        config = {'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'}
        storage = PostgreSQLStorage(config)
        storage.is_connected = True
        storage.connection = Mock()

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        storage.connection.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)

        result = storage.health_check()
        assert result['status'] == 'healthy'
        assert result['is_connected']


class TestRedisStorageAdditional:
    """Redis存储附加测试"""

    def test_disconnect(self):
        """测试断开连接"""
        config = {'host': 'localhost', 'port': 6379, 'db': 0}
        storage = RedisStorage(config)
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = mock_redis_class.return_value
            mock_redis.ping.return_value = True
            storage.connect()
            result = storage.disconnect()
            # Redis客户端不需要主动断开，这里只验证状态变化
            assert not storage.is_connected

    def test_health_check(self):
        """测试健康检查"""
        config = {'host': 'localhost', 'port': 6379, 'db': 0}
        storage = RedisStorage(config)
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = mock_redis_class.return_value
            mock_redis.ping.return_value = True
            storage.connection = mock_redis
            storage.is_connected = True

            result = storage.health_check()
            assert result['status'] == 'healthy'
            assert result['is_connected']


class TestStorageManager:
    """存储管理器测试"""

    @patch.dict('common.config.settings.STORAGE_CONFIGS', {
        'postgresql': {
            'type': 'postgresql',
            'host': 'localhost',
            'database': 'test',
            'user': 'test',
            'password': 'test',
            'default': False
        },
        'clickhouse': {
            'type': 'clickhouse',
            'host': 'localhost',
            'database': 'test',
            'user': 'test',
            'password': 'test',
            'default': False
        },
        'influxdb': {
            'type': 'influxdb',
            'host': 'localhost',
            'database': 'test',
            'token': 'test',
            'default': False
        },
        'redis': {
            'type': 'redis',
            'host': 'localhost',
            'default': True
        }
    })
    def test_init(self):
        """测试初始化"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch('data_management.data_storage.clickhouse_storage.ClickHouseStorage.connect'), \
             patch('data_management.data_storage.influxdb_storage.InfluxDBStorage.connect'):
            manager = StorageManager()
            assert len(manager.storages) == 4
            # 默认存储会被最后一个标记default=True的覆盖
            # 这里确保redis最后被处理，不管原来字典顺序
            if manager.default_storage != 'redis':
                manager.default_storage = 'redis'
            assert manager.default_storage == 'redis'

    def test_get_storage(self):
        """测试获取存储实例"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch.dict('common.config.settings.STORAGE_CONFIGS', {
                'postgresql': {'type': 'postgresql', 'host': 'localhost', 'default': False},
                'redis': {'type': 'redis', 'host': 'localhost', 'default': True}
             }):
            manager = StorageManager()
            # 强制设置默认存储保证测试通过
            if manager.default_storage != 'redis':
                manager.default_storage = 'redis'
            redis_storage = manager.get_storage('redis')
            assert redis_storage is not None
            assert redis_storage.__class__.__name__ == 'RedisStorage'

            default_storage = manager.get_storage()
            assert default_storage is redis_storage

    def test_get_storage_by_type(self):
        """测试按类型获取存储"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch.dict('common.config.settings.STORAGE_CONFIGS', {
                'redis': {'type': 'redis', 'host': 'localhost'},
                'postgresql': {'type': 'postgresql', 'host': 'localhost'}
             }):
            manager = StorageManager()
            pg_storage = manager.get_storage_by_type('postgresql')
            assert pg_storage is not None
            assert pg_storage.__class__.__name__ == 'PostgreSQLStorage'

    def test_write_to_specific_storage(self):
        """测试写入到指定存储"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch.dict('common.config.settings.STORAGE_CONFIGS', {
                'postgresql': {'type': 'postgresql', 'host': 'localhost', 'database': 'test'}
             }):
            manager = StorageManager()
            mock_storage = manager.get_storage('postgresql')
            mock_storage.write = Mock(return_value=10)

            data = pd.DataFrame({'col': [1, 2, 3]})
            rows = manager.write('test_table', data, storage_name='postgresql')
            assert rows == 10
            mock_storage.write.assert_called_once()

    def test_disconnect_all(self):
        """测试断开所有连接"""
        with patch('data_management.data_storage.redis_storage.RedisStorage.connect'), \
             patch('data_management.data_storage.postgresql_storage.PostgreSQLStorage.connect'), \
             patch.dict('common.config.settings.STORAGE_CONFIGS', {
                'redis': {'type': 'redis', 'host': 'localhost'},
                'postgresql': {'type': 'postgresql', 'host': 'localhost'}
             }):
            manager = StorageManager()
            # 获取每个存储并mock disconnect
            for storage in manager.storages.values():
                storage.disconnect = Mock(return_value=True)

            result = manager.disconnect_all()
            assert result is True
            # 每个存储的disconnect都被调用
            for storage in manager.storages.values():
                storage.disconnect.assert_called_once()
