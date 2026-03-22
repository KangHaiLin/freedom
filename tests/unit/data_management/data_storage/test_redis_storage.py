"""
Unit tests for redis_storage.py
"""

import json
import pickle
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from common.exceptions import StorageException
from data_management.data_storage.redis_storage import RedisStorage


class TestRedisStorage:
    """测试Redis存储实现"""

    def test_init_default(self):
        """测试默认初始化"""
        config = {}
        storage = RedisStorage(config)
        assert storage.host == "localhost"
        assert storage.port == 6379
        assert storage.db == 0
        assert storage.decode_responses is True
        assert storage.default_ttl == 3600

    def test_init_custom(self):
        """测试自定义初始化"""
        config = {
            "host": "redis.example.com",
            "port": 6380,
            "db": 1,
            "password": "secret",
            "decode_responses": False,
            "default_ttl": 1800,
        }
        storage = RedisStorage(config)
        assert storage.host == "redis.example.com"
        assert storage.port == 6380
        assert storage.db == 1
        assert storage.password == "secret"
        assert storage.decode_responses is False
        assert storage.default_ttl == 1800

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_connect_success(self, mock_redis_cls):
        """测试连接成功"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        result = storage.connect()

        assert result is True
        assert storage.is_connected
        assert storage.connection is mock_redis
        mock_redis.ping.assert_called_once()

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_connect_failure_raises_exception(self, mock_redis_cls):
        """测试连接失败抛出异常"""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection refused")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        with pytest.raises(StorageException, match="Redis连接失败"):
            storage.connect()
        assert not storage.is_connected

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_disconnect_success(self, mock_redis_cls):
        """测试断开连接成功"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.connect()
        result = storage.disconnect()

        assert result is True
        assert not storage.is_connected
        mock_redis.close.assert_called_once()

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_disconnect_throws_exception_returns_false(self, mock_redis_cls):
        """测试断开连接异常返回False"""
        mock_redis = Mock()
        mock_redis.close.side_effect = Exception("Close failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.connect()
        result = storage.disconnect()

        assert result is False

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_write_dataframe_json_serialized(self, mock_redis_cls):
        """测试写入DataFrame序列化为JSON"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        result = storage.write("test", df, key="test:df", ttl=300)

        assert result == 1
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test:df"
        assert call_args[0][1] == 300
        # 验证序列化后的数据是JSON
        serialized = call_args[0][2]
        assert '"col1":1' in serialized

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_write_list_dict_json_serialized(self, mock_redis_cls):
        """测试写入列表字典序列化为JSON"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        data = [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]
        result = storage.write("test", data, key="test:data", ttl=0)

        assert result == 1
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        serialized = call_args[0][1]
        parsed = json.loads(serialized)
        assert parsed == data

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_write_pickle_other_objects(self, mock_redis_cls):
        """测试其他对象使用pickle序列化"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        from datetime import datetime

        # datetime object is not list/dict/DataFrame, so it will use pickle
        dt = datetime.now()
        result = storage.write("test", dt, key="test:datetime")
        assert result == 1
        # 验证调用了setex
        assert mock_redis.setex.called or mock_redis.set.called

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_write_no_ttl_uses_set(self, mock_redis_cls):
        """测试无过期时间使用set"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.write("test", {"data": 1}, key="test:key", ttl=0)

        assert result == 1
        mock_redis.set.assert_called_once()

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_write_throws_exception_raises_storage_exception(self, mock_redis_cls):
        """测试写入异常抛出StorageException"""
        mock_redis = Mock()
        mock_redis.setex.side_effect = Exception("Write failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        with pytest.raises(StorageException, match="Redis写入失败"):
            storage.write("test", {"data": 1}, key="test:key")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_single_key_json_data(self, mock_redis_cls):
        """测试读取单个键JSON数据"""
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps({"key": "value", "data": [1, 2, 3]})
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", {"key": "test:key"})

        assert result == {"key": "value", "data": [1, 2, 3]}
        mock_redis.get.assert_called_once_with("test:key")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_single_key_dataframe(self, mock_redis_cls):
        """测试读取单个键DataFrame数据"""
        mock_redis = Mock()
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        mock_redis.get.return_value = df.to_json(orient="records")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", {"key": "test:df"})

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_single_key_pickle_object(self, mock_redis_cls):
        """测试读取单个键pickle对象"""
        mock_redis = Mock()
        obj = {"key": "value"}
        pickled = pickle.dumps(obj)
        mock_redis.get.return_value = pickled
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", {"key": "test:pickle"})
        assert result == obj

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_single_key_not_exists_returns_none(self, mock_redis_cls):
        """测试读取不存在的键返回None"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", {"key": "not_exists"})
        assert result is None

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_pattern_matches_multiple_keys(self, mock_redis_cls):
        """测试模式匹配多个键"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["test:key1", "test:key2"]
        mock_redis.get.side_effect = [
            json.dumps({"value": 1}),
            json.dumps({"value": 2}),
        ]
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", {"pattern": "test:*"})

        assert isinstance(result, dict)
        assert "test:key1" in result
        assert "test:key2" in result
        assert result["test:key1"]["value"] == 1
        assert result["test:key2"]["value"] == 2

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_no_query_returns_all_keys_with_prefix(self, mock_redis_cls):
        """测试无查询返回前缀所有键"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["test:1", "test:2", "test:3"]
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.read("test", None)

        assert result == ["test:1", "test:2", "test:3"]

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_read_throws_exception_raises_storage_exception(self, mock_redis_cls):
        """测试读取异常抛出StorageException"""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Read failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        with pytest.raises(StorageException, match="Redis读取失败"):
            storage.read("test", {"key": "test:key"})

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_delete_single_key(self, mock_redis_cls):
        """测试删除单个键"""
        mock_redis = Mock()
        mock_redis.delete.return_value = 1
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.delete("test", {"key": "test:key"})

        assert result == 1
        mock_redis.delete.assert_called_once_with("test:key")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_delete_by_pattern(self, mock_redis_cls):
        """测试按模式删除"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["test:1", "test:2"]
        mock_redis.delete.return_value = 2
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.delete("test", {"pattern": "test:*"})

        assert result == 2
        mock_redis.delete.assert_called_once()

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_delete_by_prefix(self, mock_redis_cls):
        """测试按前缀删除"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["test:1", "test:2", "test:3"]
        mock_redis.delete.return_value = 3
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.delete("test", {})

        assert result == 3

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_delete_no_matching_keys_returns_zero(self, mock_redis_cls):
        """测试无匹配键返回0"""
        mock_redis = Mock()
        mock_redis.keys.return_value = []
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.delete("test", {})

        assert result == 0

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_delete_throws_exception_raises_storage_exception(self, mock_redis_cls):
        """测试删除异常抛出StorageException"""
        mock_redis = Mock()
        mock_redis.delete.side_effect = Exception("Delete failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        with pytest.raises(StorageException, match="Redis删除失败"):
            storage.delete("test", {"key": "test:key"})

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_execute_sql_command(self, mock_redis_cls):
        """测试执行Redis命令"""
        mock_redis = Mock()
        mock_redis.execute_command.return_value = b"PONG"
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.execute_sql("PING")

        assert result == b"PONG"
        mock_redis.execute_command.assert_called_once_with("PING")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_execute_sql_empty_command_raises_exception(self, mock_redis_cls):
        """测试空命令抛出异常"""
        mock_redis = Mock()
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        with pytest.raises(StorageException, match="Redis命令为空"):
            storage.execute_sql("")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_execute_sql_throws_exception_raises_storage_exception(self, mock_redis_cls):
        """测试执行命令异常抛出StorageException"""
        mock_redis = Mock()
        mock_redis.execute_command.side_effect = Exception("Command failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        with pytest.raises(StorageException, match="Redis执行命令失败"):
            storage.execute_sql("INVALID")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_table_exists_with_keys_returns_true(self, mock_redis_cls):
        """测试前缀存在键返回True"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["test:1", "test:2"]
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.table_exists("test")

        assert result is True

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_table_exists_no_keys_returns_false(self, mock_redis_cls):
        """测试无前缀键返回False"""
        mock_redis = Mock()
        mock_redis.keys.return_value = []
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.table_exists("not_exists")

        assert result is False

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_table_exists_exception_returns_false(self, mock_redis_cls):
        """测试检查存在异常返回False"""
        mock_redis = Mock()
        mock_redis.keys.side_effect = Exception("Error")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.table_exists("test")

        assert result is False

    def test_create_table_always_returns_true(self):
        """测试创建表总是返回True"""
        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = Mock()

        result = storage.create_table("test", {})

        assert result is True

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_health_check_healthy(self, mock_redis_cls):
        """测试健康检查健康状态"""
        mock_redis = Mock()
        mock_redis.info.return_value = {"redis_version": "7.0.0"}
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage(
            {
                "host": "localhost",
                "port": 6379,
                "db": 0,
            }
        )
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.health_check()

        assert result["status"] == "healthy"
        assert result["version"] == "7.0.0"
        assert result["is_connected"] is True

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_health_check_unhealthy(self, mock_redis_cls):
        """测试健康检查不健康状态"""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage(
            {
                "host": "badhost",
                "port": 6379,
                "db": 0,
            }
        )
        storage.is_connected = False

        result = storage.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_hset_with_ttl(self, mock_redis_cls):
        """测试hset带过期时间"""
        mock_redis = Mock()
        mock_redis.hset.return_value = 2
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.hset("myhash", {"field1": "value1", "field2": "value2"}, ttl=60)

        assert result == 2
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once_with("myhash", 60)

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_hgetall(self, mock_redis_cls):
        """测试hgetall"""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {"field1": "value1", "field2": "value2"}
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.hgetall("myhash")

        assert result == {"field1": "value1", "field2": "value2"}

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_lpush(self, mock_redis_cls):
        """测试lpush"""
        mock_redis = Mock()
        mock_redis.lpush.return_value = 3
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.lpush("mylist", "a", "b", "c")

        assert result == 3
        mock_redis.lpush.assert_called_once_with("mylist", "a", "b", "c")

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_rpop(self, mock_redis_cls):
        """测试rpop"""
        mock_redis = Mock()
        mock_redis.rpop.return_value = "c"
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.rpop("mylist")

        assert result == "c"

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_publish_dict_message_json_serialized(self, mock_redis_cls):
        """测试发布字典消息序列化为JSON"""
        mock_redis = Mock()
        mock_redis.publish.return_value = 1
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        message = {"event": "update", "data": {"id": 1}}
        result = storage.publish("channel1", message)

        assert result == 1
        call_args = mock_redis.publish.call_args
        published = call_args[0][1]
        parsed = json.loads(published)
        assert parsed == message

    @patch("data_management.data_storage.redis_storage.redis.Redis")
    def test_get_ttl(self, mock_redis_cls):
        """测试获取ttl"""
        mock_redis = Mock()
        mock_redis.ttl.return_value = 120
        mock_redis_cls.return_value = mock_redis

        storage = RedisStorage({})
        storage.is_connected = True
        storage.connection = mock_redis

        result = storage.get_ttl("test:key")

        assert result == 120
