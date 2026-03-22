"""
Unit tests for base_storage.py
"""
from unittest.mock import Mock, patch

import pytest

from common.exceptions import StorageException
from data_management.data_storage.base_storage import BaseStorage


class ConcreteTestStorage(BaseStorage):
    """Concrete implementation for testing abstract base class"""

    def connect(self) -> bool:
        if self.config.get("should_fail", False):
            return False
        self.is_connected = True
        self.connection = Mock()
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.connection = None
        return True

    def write(self, table_name: str, data, **kwargs):
        return len(data)

    def read(self, table_name: str, query=None, **kwargs):
        import pandas as pd
        return pd.DataFrame()

    def delete(self, table_name: str, query, **kwargs):
        return 0

    def execute_sql(self, sql: str, **kwargs):
        return None

    def table_exists(self, table_name: str) -> bool:
        return False

    def create_table(self, table_name: str, schema: dict, **kwargs) -> bool:
        return True

    def health_check(self) -> dict:
        return {"status": "ok", "is_connected": self.is_connected}


class TestBaseStorage:
    """测试BaseStorage抽象基类"""

    def test_init_default(self):
        """测试默认初始化"""
        config = {"host": "localhost", "port": 5432}
        storage = ConcreteTestStorage(config)
        assert storage.config == config
        assert storage.connection is None
        assert not storage.is_connected

    def test_ensure_connection_already_connected(self):
        """测试ensure_connection当已连接时不做任何事"""
        storage = ConcreteTestStorage({})
        storage.is_connected = True
        storage.connection = Mock()
        # Should not throw, already connected
        storage.ensure_connection()
        assert storage.is_connected

    def test_ensure_connection_not_connected_connect_success(self):
        """测试ensure_connection当未连接时成功连接"""
        storage = ConcreteTestStorage({})
        assert not storage.is_connected
        storage.ensure_connection()
        assert storage.is_connected
        assert storage.connection is not None

    def test_ensure_connection_connect_fails_raises_exception(self):
        """测试ensure_connection当连接失败抛出StorageException"""
        storage = ConcreteTestStorage({"should_fail": True})
        assert not storage.is_connected
        with pytest.raises(StorageException, match="存储连接失败"):
            storage.ensure_connection()

    def test_ensure_connection_connect_throws_exception(self):
        """测试ensure_connection当connect抛出异常时包装为StorageException"""
        storage = ConcreteTestStorage({})
        # Override connect to throw
        def mock_connect():
            raise ConnectionError("Network error")
        storage.connect = mock_connect

        with pytest.raises(StorageException, match="存储连接失败：Network error"):
            storage.ensure_connection()

    def test_abstract_methods(self):
        """测试所有抽象方法必须被实现"""
        # Can't instantiate without implementing all abstract methods
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            BaseStorage({})
