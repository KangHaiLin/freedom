"""
ClickHouse存储适配器
实现ClickHouse列式数据库的存储操作，适用于海量时序数据存储和分析
"""
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from clickhouse_driver import Client
import logging
from datetime import datetime

from .base_storage import BaseStorage
from common.exceptions import StorageException
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class ClickHouseStorage(BaseStorage):
    """ClickHouse存储实现"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 9000)
        self.database = config.get('database', 'default')
        self.user = config.get('user', 'default')
        self.password = config.get('password', '')
        self.chunk_size = config.get('chunk_size', 10000)
        self.settings = config.get('settings', {
            'max_insert_block_size': 100000,
            'use_numpy': False
        })

    def connect(self) -> bool:
        """建立ClickHouse连接"""
        try:
            self.connection = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                settings=self.settings
            )

            # 测试连接
            self.connection.execute("SELECT 1")
            self.is_connected = True
            logger.info(f"ClickHouse连接成功：{self.host}:{self.port}/{self.database}")
            return True

        except Exception as e:
            logger.error(f"ClickHouse连接失败：{e}")
            raise StorageException(f"ClickHouse连接失败：{e}") from e

    def disconnect(self) -> bool:
        """关闭ClickHouse连接"""
        try:
            if self.connection:
                self.connection.disconnect()
            self.is_connected = False
            logger.info("ClickHouse连接已关闭")
            return True

        except Exception as e:
            logger.error(f"ClickHouse断开连接失败：{e}")
            return False

    def write(self, table_name: str, data: Union[pd.DataFrame, List[Dict]], **kwargs) -> int:
        """写入数据到ClickHouse"""
        self.ensure_connection()

        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            if df.empty:
                logger.warning("写入数据为空")
                return 0

            # ClickHouse driver可以直接处理pandas datetime类型，不需要转换
            # 保持原始数据类型可以避免类型错误

            # 批量插入 - 转为行式字典列表
            rows_written = 0
            for i in range(0, len(df), self.chunk_size):
                chunk = df.iloc[i:i + self.chunk_size]
                rows = chunk.to_dict('records')
                self.connection.execute(
                    f"INSERT INTO {table_name} VALUES",
                    rows
                )
                rows_written += len(chunk)

            logger.debug(f"ClickHouse写入成功，表：{table_name}，记录数：{rows_written}")
            return rows_written

        except Exception as e:
            logger.error(f"ClickHouse写入失败：{e}")
            raise StorageException(f"ClickHouse写入失败：{e}") from e

    def read(self, table_name: str, query: Optional[Dict] = None, **kwargs) -> pd.DataFrame:
        """从ClickHouse查询数据"""
        self.ensure_connection()

        try:
            # 构建查询SQL
            sql = f"SELECT * FROM {table_name}"

            if query:
                conditions = []
                params = []
                for key, value in query.items():
                    if isinstance(value, list):
                        placeholders = ', '.join(['%s'] * len(value))
                        conditions.append(f"{key} IN ({placeholders})")
                        params.extend(value)
                    elif isinstance(value, str) and ('%' in value or '_' in value):
                        conditions.append(f"{key} LIKE %s")
                        params.append(value)
                    else:
                        conditions.append(f"{key} = %s")
                        params.append(value)

                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)

            # 添加排序和限制
            if 'order_by' in kwargs:
                sql += f" ORDER BY {kwargs['order_by']}"
            if 'limit' in kwargs:
                sql += f" LIMIT {kwargs['limit']}"
            if 'offset' in kwargs:
                sql += f" OFFSET {kwargs['offset']}"

            logger.debug(f"ClickHouse查询SQL：{sql}")

            # 执行查询
            result = self.connection.execute(sql, params, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)

            # 转换日期时间类型
            for col in df.columns:
                if 'date' in col.lower() or 'time' in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except:
                        pass

            logger.debug(f"ClickHouse查询成功，返回{len(df)}条记录")
            return df

        except Exception as e:
            logger.error(f"ClickHouse查询失败：{e}")
            raise StorageException(f"ClickHouse查询失败：{e}") from e

    def delete(self, table_name: str, query: Dict, **kwargs) -> int:
        """从ClickHouse删除数据（注意：ClickHouse删除是异步操作）"""
        self.ensure_connection()

        try:
            conditions = []
            params = []
            for key, value in query.items():
                if isinstance(value, list):
                    placeholders = ', '.join(['%s'] * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = %s")
                    params.append(value)

            sql = f"ALTER TABLE {table_name} DELETE"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            self.connection.execute(sql, params)
            logger.debug(f"ClickHouse删除请求已提交，表：{table_name}，条件：{query}")
            return 1  # ClickHouse不返回具体删除行数

        except Exception as e:
            logger.error(f"ClickHouse删除失败：{e}")
            raise StorageException(f"ClickHouse删除失败：{e}") from e

    def execute_sql(self, sql: str, **kwargs) -> Any:
        """执行原生SQL"""
        self.ensure_connection()

        try:
            if sql.strip().upper().startswith("SELECT"):
                # 查询语句返回DataFrame
                result = self.connection.execute(sql, with_column_types=True)
                columns = [col[0] for col in result[1]]
                df = pd.DataFrame(result[0], columns=columns)
                return df
            else:
                # 执行语句返回结果
                result = self.connection.execute(sql)
                return result

        except Exception as e:
            logger.error(f"ClickHouse执行SQL失败：{e}")
            raise StorageException(f"ClickHouse执行SQL失败：{e}") from e

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        self.ensure_connection()

        try:
            result = self.connection.execute(f"EXISTS TABLE {table_name}")
            return result[0][0] == 1

        except Exception as e:
            logger.error(f"检查表存在失败：{e}")
            return False

    def create_table(self, table_name: str, schema: Dict, **kwargs) -> bool:
        """创建表"""
        self.ensure_connection()

        try:
            # 构建列定义
            columns = []
            for col_name, col_def in schema.items():
                columns.append(f"{col_name} {col_def}")

            # 引擎设置
            engine = kwargs.get('engine', 'MergeTree')
            order_by = kwargs.get('order_by', 'tuple()')
            partition_by = kwargs.get('partition_by')
            primary_key = kwargs.get('primary_key')

            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {', '.join(columns)}
                ) ENGINE = {engine}
            """

            if partition_by:
                create_sql += f" PARTITION BY {partition_by}"

            if primary_key:
                create_sql += f" PRIMARY KEY {primary_key}"

            create_sql += f" ORDER BY {order_by}"

            self.connection.execute(create_sql)
            logger.info(f"ClickHouse表创建成功：{table_name}")
            return True

        except Exception as e:
            logger.error(f"ClickHouse创建表失败：{e}")
            raise StorageException(f"ClickHouse创建表失败：{e}") from e

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            if not self.is_connected:
                self.connect()

            start_time = DateTimeUtils.now().timestamp()
            self.connection.execute("SELECT 1")
            response_time = (DateTimeUtils.now().timestamp() - start_time) * 1000

            return {
                "status": "healthy",
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "response_time": response_time,
                "is_connected": self.is_connected
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "error": str(e),
                "is_connected": self.is_connected
            }
