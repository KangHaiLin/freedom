"""
InfluxDB存储适配器
实现InfluxDB时序数据库的存储操作，适用于实时监控、指标数据存储
"""
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
from datetime import datetime

from .base_storage import BaseStorage
from common.exceptions import StorageException
from common.utils import DateTimeUtils
from common.config import settings

logger = logging.getLogger(__name__)


class InfluxDBStorage(BaseStorage):
    """InfluxDB存储实现"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.url = config.get('url', 'http://localhost:8086')
        self.token = config.get('token')
        self.org = config.get('org', 'default')
        self.bucket = config.get('bucket', 'default')
        self.timeout = config.get('timeout', 30000)
        self.precision = config.get('precision', WritePrecision.NS)

        # 测试环境和开发环境下不强制检查token（允许未配置）
        token_is_empty = not self.token or self.token == 'your-influxdb-token'
        if token_is_empty and not (settings.is_test or settings.is_development):
            raise StorageException("InfluxDB Token未配置")

    def connect(self) -> bool:
        """建立InfluxDB连接"""
        try:
            self.connection = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=self.timeout
            )

            # 测试连接
            health = self.connection.health()
            if health.status != 'pass':
                raise StorageException(f"InfluxDB健康检查失败：{health.message}")

            self.write_api = self.connection.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.connection.query_api()
            self.delete_api = self.connection.delete_api()

            self.is_connected = True
            logger.info(f"InfluxDB连接成功：{self.url}")
            return True

        except Exception as e:
            logger.error(f"InfluxDB连接失败：{e}")
            raise StorageException(f"InfluxDB连接失败：{e}") from e

    def disconnect(self) -> bool:
        """关闭InfluxDB连接"""
        try:
            if self.connection:
                self.connection.close()
            self.is_connected = False
            logger.info("InfluxDB连接已关闭")
            return True

        except Exception as e:
            logger.error(f"InfluxDB断开连接失败：{e}")
            return False

    def write(self, table_name: str, data: Union[pd.DataFrame, List[Dict]], **kwargs) -> int:
        """写入数据到InfluxDB
        Args:
            table_name: measurement名称
            data: 数据，必须包含time字段作为时间戳
            **kwargs: 其他参数，tags指定标签字段列表
        """
        self.ensure_connection()

        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            if df.empty:
                logger.warning("写入数据为空")
                return 0

            # 检查时间字段
            if 'time' not in df.columns:
                raise StorageException("InfluxDB写入数据必须包含time字段")

            # 标签字段
            tag_columns = kwargs.get('tags', [])
            # 字段字段（除了time和tags之外的所有列）
            field_columns = [col for col in df.columns if col != 'time' and col not in tag_columns]

            points = []
            for _, row in df.iterrows():
                point = Point(table_name)

                # 添加标签
                for tag in tag_columns:
                    if pd.notna(row[tag]):
                        point.tag(tag, str(row[tag]))

                # 添加字段
                for field in field_columns:
                    if pd.notna(row[field]):
                        point.field(field, row[field])

                # 添加时间
                point.time(row['time'], write_precision=self.precision)
                points.append(point)

            # 批量写入
            self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=points
            )

            rows_written = len(points)
            logger.debug(f"InfluxDB写入成功，measurement：{table_name}，记录数：{rows_written}")
            return rows_written

        except Exception as e:
            logger.error(f"InfluxDB写入失败：{e}")
            raise StorageException(f"InfluxDB写入失败：{e}") from e

    def read(self, table_name: str, query: Optional[Dict] = None, **kwargs) -> pd.DataFrame:
        """从InfluxDB查询数据
        Args:
            table_name: measurement名称
            query: 查询条件，支持start、stop、tags、fields等
            **kwargs: 其他参数
        Returns:
            查询结果DataFrame
        """
        self.ensure_connection()

        try:
            # 构建Flux查询
            flux_query = f'from(bucket: "{self.bucket}")'

            # 时间范围
            start = kwargs.get('start', '-1h')
            stop = kwargs.get('stop', 'now()')
            flux_query += f' |> range(start: {start}, stop: {stop})'

            # 选择measurement
            flux_query += f' |> filter(fn: (r) => r._measurement == "{table_name}")'

            # 标签过滤
            if query and isinstance(query, dict):
                for key, value in query.items():
                    if key not in ['start', 'stop']:
                        if isinstance(value, list):
                            conditions = ' or '.join([f'r.{key} == "{v}"' for v in value])
                            flux_query += f' |> filter(fn: (r) => {conditions})'
                        else:
                            flux_query += f' |> filter(fn: (r) => r.{key} == "{value}")'

            # 字段过滤
            if 'fields' in kwargs:
                fields = kwargs['fields']
                if isinstance(fields, list):
                    conditions = ' or '.join([f'r._field == "{f}"' for f in fields])
                    flux_query += f' |> filter(fn: (r) => {conditions})'

            # 聚合操作
            if 'aggregate' in kwargs:
                agg = kwargs['aggregate']
                flux_query += f' |> aggregateWindow(every: {agg["window"]}, fn: {agg["func"]})'

            # 透视表转换为宽格式
            flux_query += ' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

            # 重命名时间列
            flux_query += ' |> rename(columns: {_time: "time"})'

            logger.debug(f"InfluxDB Flux查询：{flux_query}")

            # 执行查询
            result = self.query_api.query_data_frame(flux_query, org=self.org)

            if isinstance(result, list):
                df = pd.concat(result, ignore_index=True)
            else:
                df = result

            # 清理不必要的列
            if not df.empty:
                keep_columns = ['time'] + [col for col in df.columns if not col.startswith('_')]
                df = df[keep_columns].copy()

            logger.debug(f"InfluxDB查询成功，返回{len(df)}条记录")
            return df

        except Exception as e:
            logger.error(f"InfluxDB查询失败：{e}")
            raise StorageException(f"InfluxDB查询失败：{e}") from e

    def delete(self, table_name: str, query: Dict, **kwargs) -> int:
        """从InfluxDB删除数据"""
        self.ensure_connection()

        try:
            start = query.get('start', '1970-01-01T00:00:00Z')
            stop = query.get('stop', DateTimeUtils.now().isoformat())

            # 构建删除谓词
            predicate = f'_measurement="{table_name}"'
            for key, value in query.items():
                if key not in ['start', 'stop']:
                    if isinstance(value, list):
                        conditions = ' or '.join([f'{key}="{v}"' for v in value])
                        predicate += f' and ({conditions})'
                    else:
                        predicate += f' and {key}="{value}"'

            self.delete_api.delete(
                start=start,
                stop=stop,
                predicate=predicate,
                bucket=self.bucket,
                org=self.org
            )

            logger.debug(f"InfluxDB删除成功，measurement：{table_name}，条件：{predicate}")
            return 1  # InfluxDB不返回具体删除行数

        except Exception as e:
            logger.error(f"InfluxDB删除失败：{e}")
            raise StorageException(f"InfluxDB删除失败：{e}") from e

    def execute_sql(self, sql: str, **kwargs) -> Any:
        """执行原生Flux查询"""
        self.ensure_connection()

        try:
            result = self.query_api.query_data_frame(sql, org=self.org)
            return result
        except Exception as e:
            logger.error(f"InfluxDB执行Flux失败：{e}")
            raise StorageException(f"InfluxDB执行Flux失败：{e}") from e

    def table_exists(self, table_name: str) -> bool:
        """检查measurement是否存在"""
        self.ensure_connection()

        try:
            flux_query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -1m)
                |> filter(fn: (r) => r._measurement == "{table_name}")
                |> limit(n: 1)
            '''
            result = self.query_api.query(flux_query, org=self.org)
            return len(result) > 0
        except Exception as e:
            logger.error(f"检查measurement存在失败：{e}")
            return False

    def create_table(self, table_name: str, schema: Dict, **kwargs) -> bool:
        """InfluxDB不需要显式创建表，写入时自动创建"""
        logger.info(f"InfluxDB measurement {table_name} 将在写入时自动创建")
        return True

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            if not self.is_connected:
                self.connect()

            health = self.connection.health()
            return {
                "status": "healthy" if health.status == 'pass' else "unhealthy",
                "url": self.url,
                "org": self.org,
                "bucket": self.bucket,
                "version": health.version,
                "is_connected": self.is_connected
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "url": self.url,
                "org": self.org,
                "bucket": self.bucket,
                "error": str(e),
                "is_connected": self.is_connected
            }
