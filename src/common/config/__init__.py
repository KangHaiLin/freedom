"""
配置管理模块
基于Pydantic实现多环境配置管理
"""

import os
from functools import lru_cache
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """数据库配置"""

    # PostgreSQL配置
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="quant", env="POSTGRES_DB")

    @property
    def postgres_url(self) -> str:
        """PostgreSQL连接URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # ClickHouse配置
    clickhouse_host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=9000, env="CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", env="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="", env="CLICKHOUSE_PASSWORD")
    clickhouse_db: str = Field(default="quant", env="CLICKHOUSE_DB")

    # InfluxDB配置
    influxdb_url: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(default="", env="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="quant", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="realtime", env="INFLUXDB_BUCKET")

    # Redis配置
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class KafkaConfig(BaseSettings):
    """Kafka配置"""

    bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    group_id: str = Field(default="quant-group", env="KAFKA_GROUP_ID")
    auto_offset_reset: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    enable_auto_commit: bool = Field(default=True, env="KAFKA_ENABLE_AUTO_COMMIT")
    auto_commit_interval_ms: int = Field(default=5000, env="KAFKA_AUTO_COMMIT_INTERVAL_MS")


class DataSourceConfig(BaseSettings):
    """数据源配置"""

    tushare_api_key: str = Field(default="", env="TUSHARE_API_KEY")
    wind_api_key: str = Field(default="", env="WIND_API_KEY")
    joinquant_api_key: str = Field(default="", env="JOINQUANT_API_KEY")
    # 数据源优先级配置，数字越小优先级越高
    akshare_priority: int = Field(default=1, env="AKSHARE_PRIORITY")
    tushare_priority: int = Field(default=5, env="TUSHARE_PRIORITY")
    wind_priority: int = Field(default=10, env="WIND_PRIORITY")
    joinquant_priority: int = Field(default=15, env="JOINQUANT_PRIORITY")
    # 数据源权重配置
    akshare_weight: float = Field(default=2.0, env="AKSHARE_WEIGHT")
    tushare_weight: float = Field(default=1.5, env="TUSHARE_WEIGHT")
    wind_weight: float = Field(default=1.0, env="WIND_WEIGHT")
    joinquant_weight: float = Field(default=1.0, env="JOINQUANT_WEIGHT")


class JaegerConfig(BaseSettings):
    """链路追踪配置"""

    agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    sampler_type: str = Field(default="const", env="JAEGER_SAMPLER_TYPE")
    sampler_param: float = Field(default=1.0, env="JAEGER_SAMPLER_PARAM")
    service_name: str = Field(default="quant-trading-system", env="JAEGER_SERVICE_NAME")


class AlertConfig(BaseSettings):
    """告警配置"""

    wechat_webhook: str = Field(default="", env="WECHAT_WEBHOOK")
    sms_api_key: str = Field(default="", env="SMS_API_KEY")
    email_smtp_server: str = Field(default="smtp.example.com", env="EMAIL_SMTP_SERVER")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    email_user: str = Field(default="", env="EMAIL_USER")
    email_password: str = Field(default="", env="EMAIL_PASSWORD")


class AppConfig(BaseSettings):
    """应用主配置"""

    model_config = {"extra": "allow"}

    env: str = Field(default="development", env="ENV")
    debug: bool = Field(default=True, env="DEBUG")
    port: int = Field(default=8000, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    secret_key: str = Field(default="your-secret-key-here-please-change-in-production", env="SECRET_KEY")
    project_name: str = Field(default="A股量化交易系统", env="PROJECT_NAME")
    PROJECT_NAME: str = Field(default="A股量化交易系统", env="PROJECT_NAME")  # 兼容大写
    version: str = Field(default="1.0.0", env="VERSION")
    VERSION: str = Field(default="1.0.0", env="VERSION")  # 兼容大写
    DEBUG: bool = Field(default=True, env="DEBUG")  # 兼容大写
    CORS_ORIGINS: list = Field(default=["*"], env="CORS_ORIGINS")  # 兼容大写
    API_KEY_ENABLED: bool = Field(default=False, env="API_KEY_ENABLED")  # 是否启用API Key验证
    API_KEYS: list = Field(default=["test_api_key"], env="API_KEYS")  # API Key列表
    JWT_SECRET_KEY: str = Field(default="test_jwt_secret", env="JWT_SECRET_KEY")  # JWT密钥
    RATE_LIMIT: int = Field(default=1000, env="RATE_LIMIT")  # 每分钟请求次数限制
    RATE_LIMIT_ENABLED: bool = Field(default=False, env="RATE_LIMIT_ENABLED")  # 是否启用限流

    # PostgreSQL配置
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="quant", env="POSTGRES_DB")

    # ClickHouse配置
    clickhouse_host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=9000, env="CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", env="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="", env="CLICKHOUSE_PASSWORD")
    clickhouse_db: str = Field(default="quant", env="CLICKHOUSE_DB")

    # InfluxDB配置
    influxdb_url: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(default="your-influxdb-token", env="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="quant", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="realtime", env="INFLUXDB_BUCKET")

    # Redis配置
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    # Kafka配置
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_group_id: str = Field(default="quant-group", env="KAFKA_GROUP_ID")
    kafka_auto_offset_reset: str = Field(default="earliest", env="KAFKA_AUTO_OFFSET_RESET")
    kafka_enable_auto_commit: bool = Field(default=True, env="KAFKA_ENABLE_AUTO_COMMIT")
    kafka_auto_commit_interval_ms: int = Field(default=5000, env="KAFKA_AUTO_COMMIT_INTERVAL_MS")

    # 数据源配置
    tushare_api_key: str = Field(default="", env="TUSHARE_API_KEY")
    wind_api_key: str = Field(default="", env="WIND_API_KEY")
    joinquant_api_key: str = Field(default="", env="JOINQUANT_API_KEY")
    akshare_priority: int = Field(default=1, env="AKSHARE_PRIORITY")
    tushare_priority: int = Field(default=5, env="TUSHARE_PRIORITY")
    wind_priority: int = Field(default=10, env="WIND_PRIORITY")
    joinquant_priority: int = Field(default=15, env="JOINQUANT_PRIORITY")
    akshare_weight: float = Field(default=2.0, env="AKSHARE_WEIGHT")
    tushare_weight: float = Field(default=1.5, env="TUSHARE_WEIGHT")
    wind_weight: float = Field(default=1.0, env="WIND_WEIGHT")
    joinquant_weight: float = Field(default=1.0, env="JOINQUANT_WEIGHT")

    # Jaeger链路追踪
    jaeger_agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    jaeger_agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    jaeger_sampler_type: str = Field(default="const", env="JAEGER_SAMPLER_TYPE")
    jaeger_sampler_param: float = Field(default=1.0, env="JAEGER_SAMPLER_PARAM")
    jaeger_service_name: str = Field(default="quant-trading-system", env="SERVICE_NAME")

    # 告警配置
    wechat_webhook: str = Field(default="", env="WECHAT_WEBHOOK")
    sms_api_key: str = Field(default="", env="SMS_API_KEY")
    email_smtp_server: str = Field(default="smtp.example.com", env="EMAIL_SMTP_SERVER")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    email_user: str = Field(default="your-email@example.com", env="EMAIL_USER")
    email_password: str = Field(default="your-email-password", env="EMAIL_PASSWORD")

    # 子配置保持兼容引用
    @property
    def database(self) -> Dict:
        return {
            "postgres_host": self.postgres_host,
            "postgres_port": self.postgres_port,
            "postgres_user": self.postgres_user,
            "postgres_password": self.postgres_password,
            "postgres_db": self.postgres_db,
            "clickhouse_host": self.clickhouse_host,
            "clickhouse_port": self.clickhouse_port,
            "clickhouse_user": self.clickhouse_user,
            "clickhouse_password": self.clickhouse_password,
            "clickhouse_db": self.clickhouse_db,
            "influxdb_url": self.influxdb_url,
            "influxdb_token": self.influxdb_token,
            "influxdb_org": self.influxdb_org,
            "influxdb_bucket": self.influxdb_bucket,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_password": self.redis_password,
            "redis_db": self.redis_db,
        }

    @property
    def kafka(self) -> Dict:
        return {
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "group_id": self.kafka_group_id,
            "auto_offset_reset": self.kafka_auto_offset_reset,
            "enable_auto_commit": self.kafka_enable_auto_commit,
            "auto_commit_interval_ms": self.kafka_auto_commit_interval_ms,
        }

    @property
    def data_sources(self) -> Dict:
        return {
            "tushare_api_key": self.tushare_api_key,
            "wind_api_key": self.wind_api_key,
            "joinquant_api_key": self.joinquant_api_key,
            "akshare_priority": self.akshare_priority,
            "tushare_priority": self.tushare_priority,
            "wind_priority": self.wind_priority,
            "joinquant_priority": self.joinquant_priority,
            "akshare_weight": self.akshare_weight,
            "tushare_weight": self.tushare_weight,
            "wind_weight": self.wind_weight,
            "joinquant_weight": self.joinquant_weight,
        }

    @property
    def jaeger(self) -> Dict:
        return {
            "agent_host": self.jaeger_agent_host,
            "agent_port": self.jaeger_agent_port,
            "sampler_type": self.jaeger_sampler_type,
            "sampler_param": self.jaeger_sampler_param,
            "service_name": self.jaeger_service_name,
        }

    @property
    def alert(self) -> Dict:
        return {
            "wechat_webhook": self.wechat_webhook,
            "sms_api_key": self.sms_api_key,
            "email_smtp_server": self.email_smtp_server,
            "email_smtp_port": self.email_smtp_port,
            "email_user": self.email_user,
            "email_password": self.email_password,
        }

    # JWT配置
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=120, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_path: str = Field(default="./logs", env="LOG_PATH")

    # 限流配置
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_MINUTE")

    # 开发模式配置
    enable_docs: bool = Field(default=True, env="ENABLE_DOCS")
    enable_cors: bool = Field(default=True, env="ENABLE_CORS")
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")

    # 数据同步任务配置
    # Cron 表达式：分 时 日 月 周
    daily_sync_cron: str = Field(default="0 16 * * *", env="DAILY_SYNC_CRON")
    minute_sync_cron: str = Field(default="0 17 * * *", env="MINUTE_SYNC_CRON")
    tick_sync_cron: str = Field(default="0 18 * * *", env="TICK_SYNC_CRON")

    # 是否启用各频率同步
    enable_daily_sync: bool = Field(default=True, env="ENABLE_DAILY_SYNC")
    enable_minute_sync: bool = Field(default=False, env="ENABLE_MINUTE_SYNC")
    enable_tick_sync: bool = Field(default=False, env="ENABLE_TICK_SYNC")

    # 同步参数配置
    sync_batch_size: int = Field(default=10, env="SYNC_BATCH_SIZE")
    sync_max_retries: int = Field(default=3, env="SYNC_MAX_RETRIES")
    sync_default_start_date: str = Field(default="2020-01-01", env="SYNC_DEFAULT_START_DATE")

    # 股票过滤配置
    filter_only_listed: bool = Field(default=True, env="FILTER_ONLY_LISTED")
    filter_exclude_st: bool = Field(default=True, env="FILTER_EXCLUDE_ST")

    @property
    # 兼容大写别名
    @property
    def DAILY_SYNC_CRON(self) -> str:
        return self.daily_sync_cron

    @property
    def MINUTE_SYNC_CRON(self) -> str:
        return self.minute_sync_cron

    @property
    def TICK_SYNC_CRON(self) -> str:
        return self.tick_sync_cron

    @property
    def ENABLE_DAILY_SYNC(self) -> bool:
        return self.enable_daily_sync

    @property
    def ENABLE_MINUTE_SYNC(self) -> bool:
        return self.enable_minute_sync

    @property
    def ENABLE_TICK_SYNC(self) -> bool:
        return self.enable_tick_sync

    @property
    def SYNC_BATCH_SIZE(self) -> int:
        return self.sync_batch_size

    @property
    def SYNC_MAX_RETRIES(self) -> int:
        return self.sync_max_retries

    @property
    def SYNC_DEFAULT_START_DATE(self) -> str:
        return self.sync_default_start_date

    @property
    def FILTER_ONLY_LISTED(self) -> bool:
        return self.filter_only_listed

    @property
    def FILTER_EXCLUDE_ST(self) -> bool:
        return self.filter_exclude_st

    @property
    def is_production(self) -> bool:
        """是否是生产环境"""
        return self.env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """是否是开发环境"""
        return self.env.lower() == "development"

    @property
    def is_test(self) -> bool:
        """是否是测试环境"""
        return self.env.lower() == "test"

    @property
    def STORAGE_CONFIGS(self) -> Dict:
        """存储配置（兼容旧代码）"""
        return {
            "postgresql": {
                "type": "postgresql",
                "host": self.postgres_host,
                "port": self.postgres_port,
                "user": self.postgres_user,
                "password": self.postgres_password,
                "database": self.postgres_db,
                "default": True,
            },
            "clickhouse": {
                "type": "clickhouse",
                "host": self.clickhouse_host,
                "port": self.clickhouse_port,
                "user": self.clickhouse_user,
                "password": self.clickhouse_password,
                "database": self.clickhouse_db,
            },
            "influxdb": {
                "type": "influxdb",
                "url": self.influxdb_url,
                "token": self.influxdb_token,
                "org": self.influxdb_org,
                "bucket": self.influxdb_bucket,
            },
            "redis": {
                "type": "redis",
                "host": self.redis_host,
                "port": self.redis_port,
                "password": self.redis_password,
                "db": self.redis_db,
            },
        }

    @property
    def QUERY_CONFIG(self) -> Dict:
        """查询配置"""
        return {
            "enable_cache": True,
            "cache_ttl": 300,
            "max_query_rows": 100000,
            "slow_query_threshold": 1.0,
            "enable_slow_query_log": True,
        }

    @property
    def ALERT_CONFIG(self) -> Dict:
        """告警配置"""
        return {
            "enabled": not self.is_test,
            "channels": ["log"],
            "default_level": "WARNING",
            "cooldown_seconds": 300,
            "webhook_url": self.wechat_webhook,
            "email_config": {
                "smtp_server": self.email_smtp_server,
                "smtp_port": self.email_smtp_port,
                "user": self.email_user,
                "password": self.email_password,
            },
        }

    @property
    def MONITOR_CONFIG(self) -> Dict:
        """监控配置"""
        return {
            "enabled": not self.is_test,
            "check_interval": 60,
            "data_quality_check_interval": 300,
            "collection_monitor_interval": 60,
            "alert_enabled": True,
            "max_consecutive_failures": 3,
            "metrics_retention_days": 30,
        }

    @property
    def REDIS_CONFIG(self) -> Dict:
        """Redis配置（兼容旧代码）"""
        return {"host": self.redis_host, "port": self.redis_port, "password": self.redis_password, "db": self.redis_db}

    @property
    def PROCESSING_CONFIG(self) -> Dict:
        """数据处理配置"""
        return {
            "enable_transformation": True,
            "enable_aggregation": True,
            "enable_indicators": True,
            "enable_normalization": True,
            "enable_merging": True,
            "enable_batch": True,
            "enable_stream": True,
            "transformation": {
                "enabled": True,
                "default_date_format": "%Y-%m-%d",
                "default_datetime_format": "%Y-%m-%d %H:%M:%S",
            },
            "indicators": {
                "enabled": True,
                "default_params": {
                    "sma": {"windows": [5, 10, 20, 60]},
                    "ema": {"windows": [12, 26]},
                    "rsi": {"window": 14},
                    "kdj": {"n": 9, "m1": 3, "m2": 3},
                    "macd": {"fast": 12, "slow": 26, "signal": 9},
                    "boll": {"window": 20, "std_dev": 2},
                    "adx": {"window": 14},
                },
            },
            "batch": {"enabled": True, "chunk_size": 10000, "max_workers": 4, "enable_parallel": True},
            "stream": {"enabled": True, "window_size": 100, "max_records": 10000, "keep_raw_data": True},
            "normalization": {"enabled": True},
            "aggregation": {"enabled": True},
            "merging": {"enabled": True},
        }

    @property
    def SYSTEM_CONFIG(self) -> Dict:
        """系统管理子系统配置"""
        return {
            "enable_config_hotreload": True,
            "enable_structured_logging": True,
            "log_level": self.log_level,
            "log_path": self.log_path,
            "log_retention_days": 30,
            "monitor_interval_seconds": 15,
            "max_concurrent_async_tasks": 10,
            "enable_background_monitoring": True,
            "health_check_interval_seconds": 60,
            "cleanup_interval_hours": 24,
            "default_log_file": "./logs/system.log",
            "default_structured_log_file": "./logs/system_structured.log",
            # 资源告警阈值
            "cpu_warning_threshold": 70,
            "cpu_critical_threshold": 90,
            "memory_warning_threshold": 80,
            "memory_critical_threshold": 95,
            "disk_warning_threshold": 85,
            "disk_critical_threshold": 95,
        }


@lru_cache()
def get_config() -> AppConfig:
    """获取全局配置实例（单例）"""
    env_file = os.getenv("ENV_FILE", ".env")
    return AppConfig(_env_file=env_file)


# 全局配置实例
config = get_config()
settings = config  # 兼容settings别名

__all__ = [
    "config",
    "settings",
    "get_config",
    "AppConfig",
    "DatabaseConfig",
    "KafkaConfig",
    "DataSourceConfig",
    "JaegerConfig",
    "AlertConfig",
]
