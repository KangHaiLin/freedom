"""
数据存储模块
负责统一管理多数据源存储，支持PostgreSQL、ClickHouse、InfluxDB、Redis等存储引擎
"""

from .base_storage import BaseStorage
from .clickhouse_storage import ClickHouseStorage
from .influxdb_storage import InfluxDBStorage
from .postgresql_storage import PostgreSQLStorage
from .redis_storage import RedisStorage
from .storage_manager import StorageManager, storage_manager

__all__ = [
    "BaseStorage",
    "PostgreSQLStorage",
    "ClickHouseStorage",
    "InfluxDBStorage",
    "RedisStorage",
    "StorageManager",
    "storage_manager",
]
