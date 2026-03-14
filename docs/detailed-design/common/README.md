# 公共模块详细设计

## 1. 概述
公共模块是所有子系统共享的基础组件，提供通用的工具类、异常定义、常量定义、配置管理等功能，减少重复代码，保持系统一致性。

## 2. 模块划分
```
common/
├── exceptions          # 异常定义
├── utils               # 工具类
├── constants           # 常量定义
├── config              # 配置管理
├── middleware          # 中间件
└── models              # 通用数据模型
```

## 3. 异常定义
### 3.1 基础异常类
```python
class BaseAppException(Exception):
    """应用基础异常类"""
    code: int = 500
    message: str = "服务器内部错误"
    details: dict = None

    def __init__(self, message: str = None, code: int = None, details: dict = None):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "error_type": self.__class__.__name__
        }
```

### 3.2 业务异常类
```python
# 参数异常
class InvalidParameterException(BaseAppException):
    code = 400
    message = "无效的请求参数"

# 认证异常
class AuthenticationException(BaseAppException):
    code = 401
    message = "用户未认证或认证已过期"

# 权限异常
class PermissionDeniedException(BaseAppException):
    code = 403
    message = "没有权限访问该资源"

# 资源不存在异常
class ResourceNotFoundException(BaseAppException):
    code = 404
    message = "请求的资源不存在"

# 限流异常
class RateLimitExceededException(BaseAppException):
    code = 429
    message = "请求过于频繁，请稍后再试"

# 业务逻辑异常
class BusinessException(BaseAppException):
    code = 400
    message = "业务逻辑错误"

# 数据异常
class DataException(BaseAppException):
    code = 500
    message = "数据处理错误"

# 第三方服务异常
class ThirdPartyServiceException(BaseAppException):
    code = 503
    message = "第三方服务调用失败"
```

## 4. 工具类设计
### 4.1 日期时间工具类
```python
from datetime import datetime, date, timedelta
from typing import Union, List
import pandas as pd
import pytz

class DateTimeUtils:
    """日期时间工具类"""

    SH_TZ = pytz.timezone('Asia/Shanghai')
    UTC_TZ = pytz.UTC

    @classmethod
    def now(cls) -> datetime:
        """获取当前上海时间"""
        return datetime.now(cls.SH_TZ)

    @classmethod
    def now_str(cls, format: str = '%Y-%m-%d %H:%M:%S') -> str:
        """获取当前时间字符串"""
        return cls.now().strftime(format)

    @classmethod
    def today(cls) -> date:
        """获取当前日期"""
        return cls.now().date()

    @classmethod
    def today_str(cls, format: str = '%Y-%m-%d') -> str:
        """获取当前日期字符串"""
        return cls.today().strftime(format)

    @classmethod
    def is_trading_day(cls, dt: Union[date, str]) -> bool:
        """判断是否是A股交易日"""
        if isinstance(dt, str):
            dt = datetime.strptime(dt, '%Y-%m-%d').date()

        # 周末不是交易日
        if dt.weekday() >= 5:
            return False

        # 节假日判断（需要接入节假日数据）
        # TODO: 实现节假日校验逻辑
        return True

    @classmethod
    def get_trading_days(cls, start_date: str, end_date: str) -> List[date]:
        """获取指定日期范围内的交易日列表"""
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        days = []
        current = start
        while current <= end:
            if cls.is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    @classmethod
    def is_trading_time(cls, dt: datetime = None) -> bool:
        """判断是否是交易时间"""
        dt = dt or cls.now()

        # 首先判断是否是交易日
        if not cls.is_trading_day(dt.date()):
            return False

        time = dt.time()

        # 早盘：9:30-11:30
        morning_start = datetime.strptime('09:30:00', '%H:%M:%S').time()
        morning_end = datetime.strptime('11:30:00', '%H:%M:%S').time()

        # 午盘：13:00-15:00
        afternoon_start = datetime.strptime('13:00:00', '%H:%M:%S').time()
        afternoon_end = datetime.strptime('15:00:00', '%H:%M:%S').time()

        return (morning_start <= time <= morning_end) or (afternoon_start <= time <= afternoon_end)
```

### 4.2 数值工具类
```python
import decimal
from typing import Union

class NumberUtils:
    """数值处理工具类"""

    DECIMAL_PRECISION = 4  # 默认保留4位小数
    PRICE_PRECISION = 2    # 价格保留2位小数
    RATIO_PRECISION = 4    # 比率保留4位小数

    @classmethod
    def round_price(cls, value: Union[float, decimal.Decimal]) -> decimal.Decimal:
        """价格四舍五入，保留2位小数"""
        return decimal.Decimal(str(value)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def round_ratio(cls, value: Union[float, decimal.Decimal]) -> decimal.Decimal:
        """比率四舍五入，保留4位小数"""
        return decimal.Decimal(str(value)).quantize(decimal.Decimal('0.0001'), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def format_money(cls, amount: Union[float, decimal.Decimal]) -> str:
        """格式化金额，保留2位小数"""
        return f"{cls.round_price(amount):,.2f}"

    @classmethod
    def format_percent(cls, ratio: Union[float, decimal.Decimal]) -> str:
        """格式化百分比，保留2位小数"""
        return f"{cls.round_ratio(ratio * 100):,.2f}%"

    @classmethod
    def is_equal(cls, a: Union[float, decimal.Decimal], b: Union[float, decimal.Decimal], precision: int = 4) -> bool:
        """判断两个数值是否相等，指定精度"""
        return abs(decimal.Decimal(str(a)) - decimal.Decimal(str(b))) < decimal.Decimal(f"1e-{precision}")
```

### 4.3 股票代码工具类
```python
class StockCodeUtils:
    """股票代码处理工具类"""

    EXCHANGE_SH = 'SH'
    EXCHANGE_SZ = 'SZ'
    EXCHANGE_BJ = 'BJ'

    @classmethod
    def normalize_code(cls, code: str) -> str:
        """标准化股票代码，转换为 代码.交易所 格式"""
        code = code.strip().upper()

        # 已经包含交易所后缀
        if '.' in code:
            parts = code.split('.')
            if len(parts) == 2:
                number, exchange = parts
                if exchange in [cls.EXCHANGE_SH, cls.EXCHANGE_SZ, cls.EXCHANGE_BJ]:
                    return code
                else:
                    # 尝试识别交易所
                    exchange = cls.guess_exchange(number)
                    return f"{number}.{exchange}"

        # 只有代码，识别交易所
        exchange = cls.guess_exchange(code)
        return f"{code}.{exchange}"

    @classmethod
    def guess_exchange(cls, code: str) -> str:
        """根据股票代码猜测交易所"""
        if len(code) != 6:
            raise ValueError(f"无效的股票代码: {code}")

        # 上交所：60开头，688（科创板），5开头（基金）
        if code.startswith(('60', '688', '5')):
            return cls.EXCHANGE_SH
        # 深交所：00开头，300（创业板），1开头（基金）
        elif code.startswith(('00', '30', '1')):
            return cls.EXCHANGE_SZ
        # 北交所：8开头，4开头
        elif code.startswith(('8', '4')):
            return cls.EXCHANGE_BJ
        else:
            raise ValueError(f"无法识别交易所的股票代码: {code}")

    @classmethod
    def get_board(cls, code: str) -> str:
        """获取股票所属板块"""
        code = cls.normalize_code(code).split('.')[0]

        if code.startswith('688'):
            return '科创板'
        elif code.startswith('30'):
            return '创业板'
        elif code.startswith('8') or code.startswith('4'):
            return '北交所'
        elif code.startswith('60') or code.startswith('00'):
            return '主板'
        else:
            return '其他'

    @classmethod
    def get_price_limit(cls, code: str, is_st: bool = False) -> float:
        """获取股票涨跌幅限制"""
        board = cls.get_board(code)

        if is_st:
            return 0.05  # ST股票5%涨跌幅
        elif board in ['科创板', '创业板', '北交所']:
            return 0.20  # 科创板、创业板、北交所20%涨跌幅
        else:
            return 0.10  # 主板10%涨跌幅
```

### 4.4 加密工具类
```python
import hmac
import hashlib
import base64
import json
from typing import Dict, Any
from datetime import datetime

class CryptoUtils:
    """加密工具类"""

    @classmethod
    def generate_hmac_signature(cls, params: Dict[str, Any], secret_key: str, timestamp: int = None, nonce: str = None) -> str:
        """生成HMAC-SHA256签名"""
        # 参数按字典序排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 添加时间戳和随机数
        timestamp = timestamp or int(datetime.now().timestamp())
        nonce = nonce or base64.b64encode(hashlib.sha256(str(datetime.now()).encode()).digest()).decode()[:8]

        sign_str = f"{param_str}&timestamp={timestamp}&nonce={nonce}"

        # 生成签名
        signature = hmac.new(
            secret_key.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    @classmethod
    def verify_hmac_signature(cls, signature: str, params: Dict[str, Any], secret_key: str, timestamp: int, nonce: str) -> bool:
        """验证HMAC-SHA256签名"""
        calculated_signature = cls.generate_hmac_signature(params, secret_key, timestamp, nonce)
        return hmac.compare_digest(calculated_signature, signature)

    @classmethod
    def hash_password(cls, password: str, salt: str) -> str:
        """密码哈希，使用PBKDF2算法"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

    @classmethod
    def generate_token(cls, length: int = 32) -> str:
        """生成随机Token"""
        return base64.b64encode(hashlib.sha256(str(datetime.now()).encode()).digest()).decode()[:length]
```

## 5. 常量定义
### 5.1 系统常量
```python
class SystemConstants:
    """系统常量"""

    # 时区
    TIME_ZONE = 'Asia/Shanghai'

    # 日期格式
    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    DATETIME_MS_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

    # 分页默认值
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000

    # JWT配置
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2小时
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7天

    # 密码盐长度
    PASSWORD_SALT_LENGTH = 16
```

### 5.2 业务常量
```python
class BusinessConstants:
    """业务常量"""

    # 交易状态
    TRADE_STATUS_NORMAL = 0  # 正常交易
    TRADE_STATUS_SUSPENDED = 1  # 停牌
    TRADE_STATUS_DELISTED = 2  # 退市

    # 订单类型
    ORDER_TYPE_BUY = 1  # 买入
    ORDER_TYPE_SELL = 2  # 卖出

    # 订单状态
    ORDER_STATUS_PENDING = 0  # 待报
    ORDER_STATUS_SUBMITTED = 1  # 已报
    ORDER_STATUS_PARTIAL_FILLED = 2  # 部分成交
    ORDER_STATUS_FILLED = 3  # 全部成交
    ORDER_STATUS_CANCELLED = 4  # 已撤销
    ORDER_STATUS_REJECTED = 5  # 废单

    # 用户角色
    ROLE_ADMIN = 'admin'  # 管理员
    ROLE_QUANT_RESEARCHER = 'quant_researcher'  # 量化研究员
    ROLE_TRADER = 'trader'  # 交易员
    ROLE_RISK_MANAGER = 'risk_manager'  # 风控经理
    ROLE_VIEWER = 'viewer'  # 查看者
```

## 6. 配置管理
### 6.1 配置结构
```python
from pydantic import BaseSettings
from typing import Dict, Optional

class DatabaseConfig(BaseSettings):
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_user: str = 'postgres'
    postgres_password: str = 'postgres'
    postgres_db: str = 'quant'

    clickhouse_host: str = 'localhost'
    clickhouse_port: int = 9000
    clickhouse_user: str = 'default'
    clickhouse_password: str = ''
    clickhouse_db: str = 'quant'

    influxdb_url: str = 'http://localhost:8086'
    influxdb_token: str = ''
    influxdb_org: str = 'quant'
    influxdb_bucket: str = 'realtime'

    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_password: str = ''
    redis_db: int = 0

class KafkaConfig(BaseSettings):
    bootstrap_servers: str = 'localhost:9092'
    group_id: str = 'quant-group'
    auto_offset_reset: str = 'earliest'

class DataSourceConfig(BaseSettings):
    tushare_api_key: str = ''
    wind_api_key: str = ''
    joinquant_api_key: str = ''

class AppConfig(BaseSettings):
    env: str = 'development'
    debug: bool = True
    port: int = 8000
    secret_key: str = 'your-secret-key-here'

    database: DatabaseConfig = DatabaseConfig()
    kafka: KafkaConfig = KafkaConfig()
    data_sources: DataSourceConfig = DataSourceConfig()

# 全局配置实例
config = AppConfig()
```

## 7. 中间件设计
### 7.1 请求日志中间件
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # 记录请求信息
        request_id = request.headers.get('X-Request-ID', 'unknown')
        user_agent = request.headers.get('User-Agent', 'unknown')
        client_ip = request.client.host if request.client else 'unknown'

        logger.info(
            f"Request start | request_id={request_id} | method={request.method} | path={request.url.path} | "
            f"client_ip={client_ip} | user_agent={user_agent}"
        )

        # 处理请求
        response = await call_next(request)

        # 记录响应信息
        process_time = (time.time() - start_time) * 1000
        status_code = response.status_code

        logger.info(
            f"Request end | request_id={request_id} | status={status_code} | process_time={process_time:.2f}ms"
        )

        response.headers['X-Process-Time'] = f"{process_time:.2f}ms"
        return response
```

### 7.2 认证中间件
```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from config import config
from utils import DateTimeUtils

class AuthMiddleware(BaseHTTPMiddleware):
    """JWT认证中间件"""

    EXCLUDE_PATHS = [
        '/api/v1/auth/login',
        '/api/v1/auth/refresh',
        '/health',
        '/docs',
        '/openapi.json'
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # 跳过不需要认证的路径
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # 获取Token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="未提供认证凭证")

        token = auth_header.split(' ')[1]

        try:
            # 验证Token
            payload = jwt.decode(token, config.secret_key, algorithms=['HS256'])

            # 检查是否过期
            if payload['exp'] < DateTimeUtils.now().timestamp():
                raise HTTPException(status_code=401, detail="Token已过期")

            # 将用户信息存入request state
            request.state.user = {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }

        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="无效的Token")

        return await call_next(request)
```

## 8. 通用数据模型
### 8.1 分页响应模型
```python
from pydantic import BaseModel
from typing import List, Generic, TypeVar

T = TypeVar('T')

class PageResponse(BaseModel, Generic[T]):
    """通用分页响应模型"""
    total: int  # 总记录数
    page: int  # 当前页码
    page_size: int  # 每页大小
    total_pages: int  # 总页数
    data: List[T]  # 数据列表

    @classmethod
    def create(cls, total: int, page: int, page_size: int, data: List[T]) -> 'PageResponse[T]':
        total_pages = (total + page_size - 1) // page_size
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=data
        )
```

### 8.2 统一响应模型
```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一API响应模型"""
    code: int = 200  # 状态码
    message: str = "success"  # 提示信息
    data: Optional[T] = None  # 返回数据
    request_id: Optional[str] = None  # 请求ID
    trace_id: Optional[str] = None  # 链路追踪ID
    timestamp: int  # 时间戳

    @classmethod
    def success(cls, data: T = None, message: str = "success", request_id: str = None, trace_id: str = None) -> 'ApiResponse[T]':
        """成功响应"""
        from utils import DateTimeUtils
        return cls(
            code=200,
            message=message,
            data=data,
            request_id=request_id,
            trace_id=trace_id,
            timestamp=int(DateTimeUtils.now().timestamp())
        )

    @classmethod
    def error(cls, code: int, message: str, details: dict = None, request_id: str = None, trace_id: str = None) -> 'ApiResponse[dict]':
        """错误响应"""
        from utils import DateTimeUtils
        return cls(
            code=code,
            message=message,
            data=details,
            request_id=request_id,
            trace_id=trace_id,
            timestamp=int(DateTimeUtils.now().timestamp())
        )
```

## 9. 分布式链路追踪方案
### 9.1 技术选型
采用OpenTelemetry作为分布式链路追踪标准，支持多语言、多框架，云原生友好：
- **链路采集**：OpenTelemetry SDK
- **链路存储**：Jaeger + Elasticsearch
- **链路可视化**：Jaeger UI + Grafana
- **采样策略**：自适应采样，错误请求100%采样，正常请求10%采样

### 9.2 集成方案
#### 9.2.1 Trace ID传递规范
- 所有请求必须携带`X-Trace-ID`、`X-Span-ID`、`X-Parent-Span-ID`头
- 服务间调用自动传递Trace上下文
- 消息队列通过消息头传递Trace上下文
- 异步任务通过任务参数传递Trace上下文

#### 9.2.2 中间件集成
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# 全局Tracer初始化
def init_tracer(service_name: str):
    trace.set_tracer_provider(TracerProvider())
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger-agent",
        agent_port=6831,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )
    return trace.get_tracer(service_name)

# FastAPI中间件
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        tracer = trace.get_tracer("api-gateway")
        # 从请求头获取Trace上下文
        trace_id = request.headers.get("X-Trace-ID")
        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            # 添加标签
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.client_ip", request.client.host)
            # 传递Trace ID到下游
            request.state.trace_id = span.get_span_context().trace_id
            response = await call_next(request)
            # 添加响应头
            response.headers["X-Trace-ID"] = format(span.get_span_context().trace_id, "x")
            return response
```

### 9.3 埋点规范
- **API网关层**：所有入口请求埋点，记录请求参数、响应状态、耗时
- **服务层**：核心业务方法埋点，记录方法参数、返回值、异常
- **数据库层**：所有SQL查询埋点，记录SQL语句、参数、执行耗时
- **缓存层**：Redis操作埋点，记录key、操作类型、耗时
- **消息队列**：消息生产和消费埋点，记录topic、消息ID、耗时
- **外部调用**：第三方接口调用埋点，记录接口地址、参数、返回值、耗时

### 9.4 采样策略
```yaml
# 采样配置
sampler:
  type: parentbased_traceidratio
  argument: 0.1  # 10%采样率
  error_sampling: true  # 错误请求100%采样
  slow_request_sampling: true  # 慢请求（>500ms）100%采样
```

### 9.5 链路分析指标
- 请求链路总耗时
- 各服务节点耗时占比
- 错误链路分布
- 慢请求链路分析
- 依赖调用关系
- 系统瓶颈识别

