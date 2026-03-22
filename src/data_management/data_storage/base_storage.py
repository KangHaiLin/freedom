"""
存储抽象基类
所有存储引擎都需要实现此接口，提供统一的存储操作
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from common.exceptions import StorageException

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """存储抽象基类"""

    def __init__(self, config: Dict):
        self.config = config
        self.connection = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        建立连接
        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        关闭连接
        Returns:
            是否关闭成功
        """
        pass

    @abstractmethod
    def write(self, table_name: str, data: Union[pd.DataFrame, List[Dict]], **kwargs) -> int:
        """
        写入数据
        Args:
            table_name: 表名
            data: 数据，可以是DataFrame或字典列表
            **kwargs: 其他参数
        Returns:
            写入的记录数
        """
        pass

    @abstractmethod
    def read(self, table_name: str, query: Optional[Dict] = None, **kwargs) -> pd.DataFrame:
        """
        查询数据
        Args:
            table_name: 表名
            query: 查询条件
            **kwargs: 其他参数
        Returns:
            查询结果DataFrame
        """
        pass

    @abstractmethod
    def delete(self, table_name: str, query: Dict, **kwargs) -> int:
        """
        删除数据
        Args:
            table_name: 表名
            query: 删除条件
            **kwargs: 其他参数
        Returns:
            删除的记录数
        """
        pass

    @abstractmethod
    def execute_sql(self, sql: str, **kwargs) -> Any:
        """
        执行原生SQL
        Args:
            sql: SQL语句
            **kwargs: 其他参数
        Returns:
            执行结果
        """
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        Args:
            table_name: 表名
        Returns:
            是否存在
        """
        pass

    @abstractmethod
    def create_table(self, table_name: str, schema: Dict, **kwargs) -> bool:
        """
        创建表
        Args:
            table_name: 表名
            schema: 表结构定义
            **kwargs: 其他参数
        Returns:
            是否创建成功
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict:
        """
        健康检查
        Returns:
            健康状态信息
        """
        pass

    def ensure_connection(self):
        """确保连接可用，如果未连接则尝试重连"""
        if not self.is_connected or not self.connection:
            try:
                success = self.connect()
                if not success:
                    raise StorageException("存储连接失败：connect() 返回 False")
            except Exception as e:
                logger.error(f"存储连接失败：{e}")
                if not isinstance(e, StorageException):
                    raise StorageException(f"存储连接失败：{e}") from e
                raise
