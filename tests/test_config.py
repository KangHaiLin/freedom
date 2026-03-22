"""
测试环境配置
"""

import os

# 数据库配置
TEST_CONFIG = {
    "postgresql": {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5433)),
        "database": os.getenv("POSTGRES_DB", "stock_test"),
        "user": os.getenv("POSTGRES_USER", "test"),
        "password": os.getenv("POSTGRES_PASSWORD", "test123"),
    },
    "clickhouse": {
        "host": os.getenv("CLICKHOUSE_HOST", "localhost"),
        "port": int(os.getenv("CLICKHOUSE_PORT", 8123)),
        "database": os.getenv("CLICKHOUSE_DB", "stock_test"),
        "user": os.getenv("CLICKHOUSE_USER", "test"),
        "password": os.getenv("CLICKHOUSE_PASSWORD", "test123"),
    },
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_DB", 0)),
        "password": os.getenv("REDIS_PASSWORD", None),
    },
    "data_sources": {
        "tushare": {
            "api_key": os.getenv("TUSHARE_API_KEY", "test_key"),
            "priority": 1,
            "weight": 2.0,
            "rate_limit": 100,
        }
    },
}

# 单元测试标记
TESTING = True
