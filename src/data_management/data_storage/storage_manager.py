"""
存储管理器
统一管理所有存储实例，提供统一的存储访问接口，支持多存储引擎路由
"""

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from common.config import settings
from common.exceptions import StorageException
from common.utils import DateTimeUtils

from .base_storage import BaseStorage
from .clickhouse_storage import ClickHouseStorage
from .influxdb_storage import InfluxDBStorage
from .postgresql_storage import PostgreSQLStorage
from .redis_storage import RedisStorage

logger = logging.getLogger(__name__)


class StorageManager:
    """存储管理器，统一管理所有存储实例"""

    def __init__(self):
        self.storages: Dict[str, BaseStorage] = {}
        self.default_storage: Optional[str] = None
        self.storage_configs = settings.STORAGE_CONFIGS
        self._load_configs()

    def _load_configs(self):
        """加载存储配置"""
        try:
            for storage_name, config in self.storage_configs.items():
                storage_type = config.get("type")
                if not storage_type:
                    logger.warning(f"存储配置{storage_name}缺少type字段，跳过")
                    continue

                # 创建存储实例
                storage = self._create_storage(storage_type, config)
                self.storages[storage_name] = storage

                # 设置默认存储
                if config.get("default", False):
                    self.default_storage = storage_name

                logger.info(f"加载存储实例：{storage_name}，类型：{storage_type}")

            if not self.default_storage and self.storages:
                self.default_storage = next(iter(self.storages.keys()))
                logger.warning(f"未配置默认存储，使用第一个存储：{self.default_storage}")

        except Exception as e:
            logger.error(f"加载存储配置失败：{e}")
            raise StorageException(f"加载存储配置失败：{e}") from e

    def _create_storage(self, storage_type: str, config: Dict) -> BaseStorage:
        """根据类型创建存储实例"""
        storage_type = storage_type.lower()
        if storage_type == "postgresql":
            return PostgreSQLStorage(config)
        elif storage_type == "clickhouse":
            return ClickHouseStorage(config)
        elif storage_type == "influxdb":
            return InfluxDBStorage(config)
        elif storage_type == "redis":
            return RedisStorage(config)
        else:
            raise StorageException(f"不支持的存储类型：{storage_type}")

    def get_storage(self, storage_name: Optional[str] = None) -> BaseStorage:
        """获取存储实例
        Args:
            storage_name: 存储名称，为空则返回默认存储
        Returns:
            存储实例
        """
        storage_name = storage_name or self.default_storage
        if not storage_name:
            raise StorageException("无可用存储实例")

        if storage_name not in self.storages:
            raise StorageException(f"存储实例不存在：{storage_name}")

        return self.storages[storage_name]

    def write(
        self, table_name: str, data: Union[pd.DataFrame, List[Dict]], storage_name: Optional[str] = None, **kwargs
    ) -> int:
        """写入数据
        Args:
            table_name: 表名/measurement名/键前缀
            data: 要写入的数据
            storage_name: 存储名称，为空则使用默认存储
            **kwargs: 其他参数
        Returns:
            写入的记录数
        """
        storage = self.get_storage(storage_name)
        return storage.write(table_name, data, **kwargs)

    def read(
        self, table_name: str, query: Optional[Dict] = None, storage_name: Optional[str] = None, **kwargs
    ) -> pd.DataFrame:
        """查询数据
        Args:
            table_name: 表名/measurement名/键前缀
            query: 查询条件
            storage_name: 存储名称，为空则使用默认存储
            **kwargs: 其他参数
        Returns:
            查询结果
        """
        storage = self.get_storage(storage_name)
        return storage.read(table_name, query, **kwargs)

    def delete(self, table_name: str, query: Dict, storage_name: Optional[str] = None, **kwargs) -> int:
        """删除数据
        Args:
            table_name: 表名/measurement名/键前缀
            query: 删除条件
            storage_name: 存储名称，为空则使用默认存储
            **kwargs: 其他参数
        Returns:
            删除的记录数
        """
        storage = self.get_storage(storage_name)
        return storage.delete(table_name, query, **kwargs)

    def execute_sql(self, sql: str, storage_name: Optional[str] = None, **kwargs) -> Any:
        """执行原生SQL/Flux/命令
        Args:
            sql: 要执行的SQL语句或命令
            storage_name: 存储名称，为空则使用默认存储
            **kwargs: 其他参数
        Returns:
            执行结果
        """
        storage = self.get_storage(storage_name)
        return storage.execute_sql(sql, **kwargs)

    def table_exists(self, table_name: str, storage_name: Optional[str] = None) -> bool:
        """检查表是否存在
        Args:
            table_name: 表名
            storage_name: 存储名称
        Returns:
            是否存在
        """
        storage = self.get_storage(storage_name)
        return storage.table_exists(table_name)

    def create_table(self, table_name: str, schema: Dict, storage_name: Optional[str] = None, **kwargs) -> bool:
        """创建表
        Args:
            table_name: 表名
            schema: 表结构
            storage_name: 存储名称
            **kwargs: 其他参数
        Returns:
            是否创建成功
        """
        storage = self.get_storage(storage_name)
        return storage.create_table(table_name, schema, **kwargs)

    def health_check(self) -> Dict:
        """所有存储实例健康检查
        Returns:
            健康检查结果
        """
        health_status = {
            "total_storages": len(self.storages),
            "healthy_storages": 0,
            "default_storage": self.default_storage,
            "storages": {},
            "check_time": DateTimeUtils.now_str(),
        }

        for name, storage in self.storages.items():
            try:
                status = storage.health_check()
                health_status["storages"][name] = status
                if status.get("status") == "healthy":
                    health_status["healthy_storages"] += 1
            except Exception as e:
                health_status["storages"][name] = {"status": "unhealthy", "error": str(e)}

        health_status["health_score"] = (
            health_status["healthy_storages"] / health_status["total_storages"]
            if health_status["total_storages"] > 0
            else 0
        )
        return health_status

    def connect_all(self) -> bool:
        """连接所有存储实例"""
        all_success = True
        for name, storage in self.storages.items():
            try:
                storage.connect()
                logger.info(f"存储{name}连接成功")
            except Exception as e:
                logger.error(f"存储{name}连接失败：{e}")
                all_success = False
        return all_success

    def disconnect_all(self) -> bool:
        """断开所有存储实例连接"""
        all_success = True
        for name, storage in self.storages.items():
            try:
                storage.disconnect()
                logger.info(f"存储{name}连接已断开")
            except Exception as e:
                logger.error(f"存储{name}断开连接失败：{e}")
                all_success = False
        return all_success

    def get_storage_by_type(self, storage_type: str) -> Optional[BaseStorage]:
        """根据存储类型获取第一个匹配的存储实例
        Args:
            storage_type: 存储类型（postgresql/clickhouse/influxdb/redis）
        Returns:
            存储实例，不存在返回None
        """
        storage_type = storage_type.lower()
        for storage in self.storages.values():
            if storage.__class__.__name__.lower().startswith(storage_type):
                return storage
        return None


# 全局存储管理器实例
storage_manager = StorageManager()
