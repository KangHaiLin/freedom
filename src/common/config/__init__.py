"""
配置管理模块
基于Pydantic实现多环境配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, Optional
import os
from functools import lru_cache


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    # PostgreSQL配置
    postgres_host: str = Field(default='localhost', env='POSTGRES_HOST')
    postgres_port: int = Field(default=5432, env='POSTGRES_PORT')
    postgres_user: str = Field(default='postgres', env='POSTGRES_USER')
    postgres_password: str = Field(default='postgres', env='POSTGRES_PASSWORD')
    postgres_db: str = Field(default='quant', env='POSTGRES_DB')

    @property
    def postgres_url(self) -> str:
        """PostgreSQL连接URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # ClickHouse配置
    clickhouse_host: str = Field(default='localhost', env='CLICKHOUSE_HOST')
    clickhouse_port: int = Field(default=9000, env='CLICKHOUSE_PORT')
    clickhouse_user: str = Field(default='default', env='CLICKHOUSE_USER')
    clickhouse_password: str = Field(default='', env='CLICKHOUSE_PASSWORD')
    clickhouse_db: str = Field(default='quant', env='CLICKHOUSE_DB')

    # InfluxDB配置
    influxdb_url: str = Field(default='http://localhost:8086', env='INFLUXDB_URL')
    influxdb_token: str = Field(default='', env='INFLUXDB_TOKEN')
    influxdb_org: str = Field(default='quant', env='INFLUXDB_ORG')
    influxdb_bucket: str = Field(default='realtime', env='INFLUXDB_BUCKET')

    # Redis配置
    redis_host: str = Field(default='localhost', env='REDIS_HOST')
    redis_port: int = Field(default=6379, env='REDIS_PORT')
    redis_password: str = Field(default='', env='REDIS_PASSWORD')
    redis_db: int = Field(default=0, env='REDIS_DB')

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class KafkaConfig(BaseSettings):
    """Kafka配置"""
    bootstrap_servers: str = Field(default='localhost:9092', env='KAFKA_BOOTSTRAP_SERVERS')
    group_id: str = Field(default='quant-group', env='KAFKA_GROUP_ID')
    auto_offset_reset: str = Field(default='earliest', env='KAFKA_AUTO_OFFSET_RESET')
    enable_auto_commit: bool = Field(default=True, env='KAFKA_ENABLE_AUTO_COMMIT')
    auto_commit_interval_ms: int = Field(default=5000, env='KAFKA_AUTO_COMMIT_INTERVAL_MS')


class DataSourceConfig(BaseSettings):
    """数据源配置"""
    tushare_api_key: str = Field(default='', env='TUSHARE_API_KEY')
    wind_api_key: str = Field(default='', env='WIND_API_KEY')
    joinquant_api_key: str = Field(default='', env='JOINQUANT_API_KEY')


class JaegerConfig(BaseSettings):
    """链路追踪配置"""
    agent_host: str = Field(default='localhost', env='JAEGER_AGENT_HOST')
    agent_port: int = Field(default=6831, env='JAEGER_AGENT_PORT')
    sampler_type: str = Field(default='const', env='JAEGER_SAMPLER_TYPE')
    sampler_param: float = Field(default=1.0, env='JAEGER_SAMPLER_PARAM')
    service_name: str = Field(default='quant-trading-system', env='JAEGER_SERVICE_NAME')


class AlertConfig(BaseSettings):
    """告警配置"""
    wechat_webhook: str = Field(default='', env='WECHAT_WEBHOOK')
    sms_api_key: str = Field(default='', env='SMS_API_KEY')
    email_smtp_server: str = Field(default='smtp.example.com', env='EMAIL_SMTP_SERVER')
    email_smtp_port: int = Field(default=587, env='EMAIL_SMTP_PORT')
    email_user: str = Field(default='', env='EMAIL_USER')
    email_password: str = Field(default='', env='EMAIL_PASSWORD')


class AppConfig(BaseSettings):
    """应用主配置"""
    env: str = Field(default='development', env='ENV')
    debug: bool = Field(default=True, env='DEBUG')
    port: int = Field(default=8000, env='PORT')
    host: str = Field(default='0.0.0.0', env='HOST')
    secret_key: str = Field(default='your-secret-key-here-please-change-in-production', env='SECRET_KEY')

    # 子配置
    database: DatabaseConfig = DatabaseConfig()
    kafka: KafkaConfig = KafkaConfig()
    data_sources: DataSourceConfig = DataSourceConfig()
    jaeger: JaegerConfig = JaegerConfig()
    alert: AlertConfig = AlertConfig()

    # JWT配置
    jwt_algorithm: str = Field(default='HS256', env='JWT_ALGORITHM')
    jwt_access_token_expire_minutes: int = Field(default=120, env='JWT_ACCESS_TOKEN_EXPIRE_MINUTES')
    jwt_refresh_token_expire_days: int = Field(default=7, env='JWT_REFRESH_TOKEN_EXPIRE_DAYS')

    # 日志配置
    log_level: str = Field(default='INFO', env='LOG_LEVEL')
    log_path: str = Field(default='./logs', env='LOG_PATH')

    # 限流配置
    rate_limit_enabled: bool = Field(default=True, env='RATE_LIMIT_ENABLED')
    rate_limit_requests_per_minute: int = Field(default=1000, env='RATE_LIMIT_REQUESTS_PER_MINUTE')

    # 开发模式配置
    enable_docs: bool = Field(default=True, env='ENABLE_DOCS')
    enable_cors: bool = Field(default=True, env='ENABLE_CORS')
    cors_origins: list = Field(default=["*"], env='CORS_ORIGINS')

    @property
    def is_production(self) -> bool:
        """是否是生产环境"""
        return self.env.lower() == 'production'

    @property
    def is_development(self) -> bool:
        """是否是开发环境"""
        return self.env.lower() == 'development'

    @property
    def is_test(self) -> bool:
        """是否是测试环境"""
        return self.env.lower() == 'test'


@lru_cache()
def get_config() -> AppConfig:
    """获取全局配置实例（单例）"""
    env_file = os.getenv("ENV_FILE", ".env")
    return AppConfig(_env_file=env_file)


# 全局配置实例
config = get_config()
settings = config  # 兼容settings别名

__all__ = [
    'config',
    'settings',
    'get_config',
    'AppConfig',
    'DatabaseConfig',
    'KafkaConfig',
    'DataSourceConfig',
    'JaegerConfig',
    'AlertConfig'
]
