"""
PostgreSQL存储适配器
实现PostgreSQL数据库的存储操作
"""

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine

from common.exceptions import StorageException
from common.utils import DateTimeUtils

from .base_storage import BaseStorage

logger = logging.getLogger(__name__)


class PostgreSQLStorage(BaseStorage):
    """PostgreSQL存储实现"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.database = config.get("database")
        self.user = config.get("user")
        self.password = config.get("password")
        self.schema = config.get("schema", "public")
        self.chunk_size = config.get("chunk_size", 1000)

        # 构建连接字符串
        self.conn_str = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.engine = None

    def connect(self) -> bool:
        """建立PostgreSQL连接"""
        try:
            # 首先使用psycopg2测试连接
            self.connection = psycopg2.connect(
                host=self.host, port=self.port, database=self.database, user=self.user, password=self.password
            )
            self.connection.autocommit = True

            # 创建SQLAlchemy引擎用于DataFrame操作
            self.engine = create_engine(self.conn_str)

            self.is_connected = True
            logger.info(f"PostgreSQL连接成功：{self.host}:{self.port}/{self.database}")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL连接失败：{e}")
            raise StorageException(f"PostgreSQL连接失败：{e}") from e

    def disconnect(self) -> bool:
        """关闭PostgreSQL连接"""
        try:
            if self.connection:
                self.connection.close()
            if self.engine:
                self.engine.dispose()
            self.is_connected = False
            logger.info("PostgreSQL连接已关闭")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL断开连接失败：{e}")
            return False

    def write(self, table_name: str, data: Union[pd.DataFrame, List[Dict]], **kwargs) -> int:
        """写入数据到PostgreSQL"""
        self.ensure_connection()

        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            if df.empty:
                logger.warning("写入数据为空")
                return 0

            # 写入数据
            rows_written = 0
            if kwargs.get("if_exists") == "append" or len(df) < 1000:
                # 小数据量使用to_sql
                df.to_sql(
                    name=table_name,
                    con=self.engine,
                    schema=self.schema,
                    if_exists=kwargs.get("if_exists", "append"),
                    index=False,
                    chunksize=self.chunk_size,
                )
                rows_written = len(df)
            else:
                # 大数据量使用execute_values批量插入
                columns = df.columns.tolist()
                records = df.values.tolist()

                with self.connection.cursor() as cur:
                    insert_query = f"""
                        INSERT INTO {self.schema}.{table_name} ({', '.join(columns)})
                        VALUES %s
                        ON CONFLICT DO NOTHING
                    """
                    execute_values(cur, insert_query, records)
                    rows_written = cur.rowcount

            logger.debug(f"PostgreSQL写入成功，表：{table_name}，记录数：{rows_written}")
            return rows_written

        except Exception as e:
            logger.error(f"PostgreSQL写入失败：{e}")
            raise StorageException(f"PostgreSQL写入失败：{e}") from e

    def read(self, table_name: str, query: Optional[Dict] = None, **kwargs) -> pd.DataFrame:
        """从PostgreSQL查询数据"""
        self.ensure_connection()

        try:
            # 构建查询SQL
            sql = f"SELECT * FROM {self.schema}.{table_name}"

            if query:
                conditions = []
                params = []
                for key, value in query.items():
                    if isinstance(value, list):
                        placeholders = ", ".join(["%s"] * len(value))
                        conditions.append(f"{key} IN ({placeholders})")
                        params.extend(value)
                    elif isinstance(value, tuple) and len(value) == 2:
                        # 范围查询 (start, end)
                        conditions.append(f"{key} >= %s AND {key} <= %s")
                        params.extend(value)
                    elif isinstance(value, str) and ("%" in value or "_" in value):
                        conditions.append(f"{key} LIKE %s")
                        params.append(value)
                    else:
                        conditions.append(f"{key} = %s")
                        params.append(value)

                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)

            # 添加排序和限制
            if "order_by" in kwargs:
                order_by = kwargs["order_by"]
                if order_by is not None:
                    if isinstance(order_by, list):
                        # 处理列表形式的排序，支持-前缀表示降序
                        order_parts = []
                        for col in order_by:
                            if col.startswith("-"):
                                order_parts.append(f"{col[1:]} DESC")
                            else:
                                order_parts.append(f"{col} ASC")
                        order_by_str = ", ".join(order_parts)
                    else:
                        order_by_str = str(order_by)
                    sql += f" ORDER BY {order_by_str}"
            if "limit" in kwargs and kwargs["limit"] is not None:
                sql += f" LIMIT {kwargs['limit']}"
            if "offset" in kwargs and kwargs["offset"] is not None:
                sql += f" OFFSET {kwargs['offset']}"

            logger.debug(f"PostgreSQL查询SQL：{sql}")

            df = pd.read_sql(sql, con=self.engine, params=params if query else None)
            logger.debug(f"PostgreSQL查询成功，返回{len(df)}条记录")
            return df

        except Exception as e:
            logger.error(f"PostgreSQL查询失败：{e}")
            raise StorageException(f"PostgreSQL查询失败：{e}") from e

    def delete(self, table_name: str, query: Dict, **kwargs) -> int:
        """从PostgreSQL删除数据"""
        self.ensure_connection()

        try:
            conditions = []
            params = []
            for key, value in query.items():
                if isinstance(value, list):
                    placeholders = ", ".join(["%s"] * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                elif isinstance(value, tuple) and len(value) == 2:
                    # 范围查询 (start, end)
                    conditions.append(f"{key} >= %s AND {key} <= %s")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = %s")
                    params.append(value)

            sql = f"DELETE FROM {self.schema}.{table_name}"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            with self.connection.cursor() as cur:
                cur.execute(sql, params)
                deleted_rows = cur.rowcount

            logger.debug(f"PostgreSQL删除成功，表：{table_name}，删除记录数：{deleted_rows}")
            return deleted_rows

        except Exception as e:
            logger.error(f"PostgreSQL删除失败：{e}")
            raise StorageException(f"PostgreSQL删除失败：{e}") from e

    def execute_sql(self, sql: str, **kwargs) -> Any:
        """执行原生SQL"""
        self.ensure_connection()

        try:
            if sql.strip().upper().startswith("SELECT"):
                # 查询语句返回DataFrame
                df = pd.read_sql(sql, con=self.engine)
                return df
            else:
                # 执行语句返回影响行数
                with self.connection.cursor() as cur:
                    cur.execute(sql)
                    return cur.rowcount

        except Exception as e:
            logger.error(f"PostgreSQL执行SQL失败：{e}")
            raise StorageException(f"PostgreSQL执行SQL失败：{e}") from e

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        self.ensure_connection()

        try:
            sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = %s
                )
            """
            with self.connection.cursor() as cur:
                cur.execute(sql, (self.schema, table_name))
                return cur.fetchone()[0]

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

            # 添加主键
            if "primary_key" in kwargs:
                pk_columns = kwargs["primary_key"]
                if isinstance(pk_columns, list):
                    columns.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
                else:
                    columns.append(f"PRIMARY KEY ({pk_columns})")

            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
                    {', '.join(columns)}
                )
            """

            with self.connection.cursor() as cur:
                cur.execute(create_sql)

            logger.info(f"PostgreSQL表创建成功：{table_name}")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL创建表失败：{e}")
            raise StorageException(f"PostgreSQL创建表失败：{e}") from e

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            if not self.is_connected:
                self.connect()

            with self.connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

            return {
                "status": "healthy",
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "response_time": DateTimeUtils.now().timestamp(),
                "is_connected": self.is_connected,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "error": str(e),
                "is_connected": self.is_connected,
            }
