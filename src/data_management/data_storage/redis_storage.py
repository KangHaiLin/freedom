"""
Redis存储适配器
实现Redis缓存的存储操作，适用于高频访问数据、缓存、分布式锁等场景
"""

import json
import logging
import pickle
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import redis

from common.exceptions import StorageException
from common.utils import DateTimeUtils

from .base_storage import BaseStorage

logger = logging.getLogger(__name__)


class RedisStorage(BaseStorage):
    """Redis存储实现"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6379)
        self.db = config.get("db", 0)
        self.password = config.get("password")
        self.decode_responses = config.get("decode_responses", True)
        self.default_ttl = config.get("default_ttl", 3600)  # 默认过期时间1小时
        self.socket_timeout = config.get("socket_timeout", 5)
        self.socket_connect_timeout = config.get("socket_connect_timeout", 5)

    def connect(self) -> bool:
        """建立Redis连接"""
        try:
            self.connection = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
            )

            # 测试连接
            self.connection.ping()
            self.is_connected = True
            logger.info(f"Redis连接成功：{self.host}:{self.port}/{self.db}")
            return True

        except Exception as e:
            logger.error(f"Redis连接失败：{e}")
            raise StorageException(f"Redis连接失败：{e}") from e

    def disconnect(self) -> bool:
        """关闭Redis连接"""
        try:
            if self.connection:
                self.connection.close()
            self.is_connected = False
            logger.info("Redis连接已关闭")
            return True

        except Exception as e:
            logger.error(f"Redis断开连接失败：{e}")
            return False

    def write(self, table_name: str, data: Union[pd.DataFrame, List[Dict], Any], **kwargs) -> int:
        """写入数据到Redis
        Args:
            table_name: 键前缀，相当于表名
            data: 数据，可以是DataFrame、字典列表或任意可序列化对象
            **kwargs: 其他参数，key指定具体键名，ttl指定过期时间
        Returns:
            写入的记录数
        """
        self.ensure_connection()

        try:
            ttl = kwargs.get("ttl", self.default_ttl)
            key = kwargs.get("key", f"{table_name}:{DateTimeUtils.now_str()}")

            # 序列化数据
            if isinstance(data, pd.DataFrame):
                # DataFrame序列化为JSON
                serialized = data.to_json(orient="records")
            elif isinstance(data, (list, dict)):
                # 列表/字典序列化为JSON
                serialized = json.dumps(data, ensure_ascii=False, default=str)
            else:
                # 其他对象使用pickle序列化
                serialized = pickle.dumps(data)
                # 关闭decode_responses以支持二进制数据
                if self.decode_responses:
                    self.connection = redis.Redis(
                        host=self.host,
                        port=self.port,
                        db=self.db,
                        password=self.password,
                        decode_responses=False,
                        socket_timeout=self.socket_timeout,
                        socket_connect_timeout=self.socket_connect_timeout,
                    )

            # 写入数据
            if ttl > 0:
                self.connection.setex(key, ttl, serialized)
            else:
                self.connection.set(key, serialized)

            logger.debug(f"Redis写入成功，键：{key}，大小：{len(serialized)}字节")
            return 1

        except Exception as e:
            logger.error(f"Redis写入失败：{e}")
            raise StorageException(f"Redis写入失败：{e}") from e

    def read(self, table_name: str, query: Optional[Dict] = None, **kwargs) -> Any:
        """从Redis读取数据
        Args:
            table_name: 键前缀
            query: 查询条件，key指定具体键名，pattern指定匹配模式
            **kwargs: 其他参数
        Returns:
            读取到的数据，自动反序列化
        """
        self.ensure_connection()

        try:
            if query and "key" in query:
                # 读取单个键
                key = query["key"]
                value = self.connection.get(key)

                if value is None:
                    return None

                # 尝试反序列化
                try:
                    # 尝试JSON反序列化
                    parsed = json.loads(value)
                    # 如果解析后是列表且每个元素是字典，则假定这是DataFrame保存为orient='records'，转换回DataFrame
                    if isinstance(parsed, list) and len(parsed) > 0 and all(isinstance(item, dict) for item in parsed):
                        return pd.DataFrame(parsed)
                    return parsed
                except Exception:
                    try:
                        # 尝试DataFrame反序列化
                        return pd.read_json(value)
                    except Exception:
                        try:
                            # 尝试pickle反序列化
                            return pickle.loads(value)
                        except Exception:
                            # 返回原始值
                            return value

            elif query and "pattern" in query:
                # 匹配多个键
                pattern = query["pattern"]
                keys = self.connection.keys(pattern)
                result = {}

                for key in keys:
                    value = self.connection.get(key)
                    try:
                        result[key] = json.loads(value)
                    except Exception:
                        result[key] = value

                return result

            else:
                # 返回指定前缀的所有键
                keys = self.connection.keys(f"{table_name}:*")
                return keys

        except Exception as e:
            logger.error(f"Redis读取失败：{e}")
            raise StorageException(f"Redis读取失败：{e}") from e

    def delete(self, table_name: str, query: Dict, **kwargs) -> int:
        """从Redis删除数据"""
        self.ensure_connection()

        try:
            if "key" in query:
                key = query["key"]
                deleted = self.connection.delete(key)
                logger.debug(f"Redis删除成功，键：{key}")
                return deleted
            elif "pattern" in query:
                pattern = query["pattern"]
                keys = self.connection.keys(pattern)
                if keys:
                    deleted = self.connection.delete(*keys)
                    logger.debug(f"Redis批量删除成功，匹配模式：{pattern}，删除键数：{deleted}")
                    return deleted
                return 0
            else:
                # 删除指定前缀的所有键
                keys = self.connection.keys(f"{table_name}:*")
                if keys:
                    deleted = self.connection.delete(*keys)
                    logger.debug(f"Redis删除前缀成功，前缀：{table_name}，删除键数：{deleted}")
                    return deleted
                return 0

        except Exception as e:
            logger.error(f"Redis删除失败：{e}")
            raise StorageException(f"Redis删除失败：{e}") from e

    def execute_sql(self, sql: str, **kwargs) -> Any:
        """执行Redis命令"""
        self.ensure_connection()

        try:
            # 解析命令
            parts = sql.split()
            if not parts:
                raise StorageException("Redis命令为空")

            cmd = parts[0].upper()
            args = parts[1:]

            # 执行命令
            result = self.connection.execute_command(cmd, *args)
            return result

        except Exception as e:
            logger.error(f"Redis执行命令失败：{e}")
            raise StorageException(f"Redis执行命令失败：{e}") from e

    def table_exists(self, table_name: str) -> bool:
        """检查是否存在该前缀的键"""
        self.ensure_connection()

        try:
            keys = self.connection.keys(f"{table_name}:*")
            return len(keys) > 0
        except Exception as e:
            logger.error(f"检查键前缀失败：{e}")
            return False

    def create_table(self, table_name: str, schema: Dict, **kwargs) -> bool:
        """Redis不需要显式创建表"""
        logger.info(f"Redis键前缀 {table_name} 已准备好，写入时自动创建")
        return True

    def health_check(self) -> Dict:
        """健康检查"""
        try:
            if not self.is_connected:
                self.connect()

            start_time = DateTimeUtils.now().timestamp()
            self.connection.ping()
            response_time = (DateTimeUtils.now().timestamp() - start_time) * 1000

            info = self.connection.info("server")
            return {
                "status": "healthy",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "version": info.get("redis_version"),
                "response_time": response_time,
                "is_connected": self.is_connected,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "error": str(e),
                "is_connected": self.is_connected,
            }

    # 额外的Redis专用方法
    def hset(self, key: str, mapping: Dict, ttl: int = None) -> int:
        """哈希表设置"""
        self.ensure_connection()
        result = self.connection.hset(key, mapping=mapping)
        if ttl:
            self.connection.expire(key, ttl)
        return result

    def hgetall(self, key: str) -> Dict:
        """获取整个哈希表"""
        self.ensure_connection()
        return self.connection.hgetall(key)

    def lpush(self, key: str, *values) -> int:
        """列表左推"""
        self.ensure_connection()
        return self.connection.lpush(key, *values)

    def rpop(self, key: str) -> Any:
        """列表右弹"""
        self.ensure_connection()
        return self.connection.rpop(key)

    def publish(self, channel: str, message: Union[str, Dict]) -> int:
        """发布消息"""
        self.ensure_connection()
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False, default=str)
        return self.connection.publish(channel, message)

    def get_ttl(self, key: str) -> int:
        """获取键的剩余过期时间"""
        self.ensure_connection()
        return self.connection.ttl(key)
