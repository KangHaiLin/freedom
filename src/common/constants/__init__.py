"""
公共常量定义
"""
from enum import Enum
from typing import Dict, Any

# 数据质量校验规则
DEFAULT_QUALITY_RULES: Dict[str, Any] = {
    # 完整性规则
    'completeness_threshold': 0.95,  # 数据完整度阈值
    'missing_value_fill_enabled': True,  # 是否启用缺失值填充

    # 准确性规则
    'accuracy_threshold': 0.99,  # 数据准确率阈值
    'price_min': 0.01,  # 最小价格
    'price_max': 10000.0,  # 最大价格
    'volume_min': 0,  # 最小成交量
    'volume_max': 10**10,  # 最大成交量
    'price_change_threshold': 0.2,  # 价格涨跌幅阈值（20%）
    'volume_change_threshold': 10,  # 成交量变化阈值（10倍均值）

    # 时效性规则
    'timeliness_threshold': 300,  # 数据时效性阈值（秒）
    'realtime_data_delay_max': 300,  # 实时数据最大延迟（秒）
    'daily_data_delay_max': 3600,  # 日线数据最大延迟（秒）

    # 一致性规则
    'consistency_threshold': 0.99,  # 数据一致性阈值
    'price_tolerance': 0.01,  # 价格比较容忍度（1分）

    # 整体质量阈值
    'overall_score_threshold': 0.8,  # 整体质量得分阈值
    'excellent_score_threshold': 0.95,  # 优秀质量得分阈值
    'good_score_threshold': 0.8,  # 良好质量得分阈值
    'poor_score_threshold': 0.6,  # 较差质量得分阈值

    # 数据清洗规则
    'duplicate_removal_enabled': True,  # 是否启用去重
    'outlier_detection_enabled': True,  # 是否启用异常值检测
    'standardization_enabled': True,  # 是否启用标准化
    'price_limit_validation_enabled': True,  # 是否启用涨跌停校验
}


class SystemConstants:
    """系统常量"""

    # 时区
    TIME_ZONE = 'Asia/Shanghai'

    # 日期格式
    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    DATETIME_MS_FORMAT = '%Y-%m-%d %H:%M:%S.%f'
    TIME_FORMAT = '%H:%M:%S'

    # 分页默认值
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000
    DEFAULT_PAGE = 1

    # JWT配置
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2小时
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7天

    # 密码盐长度
    PASSWORD_SALT_LENGTH = 16

    # API版本
    API_VERSION = 'v1'

    # 接口签名有效期（秒）
    SIGNATURE_EXPIRE_SECONDS = 300  # 5分钟

    # 系统默认用户
    DEFAULT_ADMIN_USER_ID = 1
    DEFAULT_SYSTEM_USER_ID = 0

    # 链路追踪
    TRACE_ID_HEADER = 'X-Trace-ID'
    SPAN_ID_HEADER = 'X-Span-ID'
    PARENT_SPAN_ID_HEADER = 'X-Parent-Span-ID'
    REQUEST_ID_HEADER = 'X-Request-ID'


class BusinessConstants:
    """业务常量"""

    # 交易状态
    TRADE_STATUS_NORMAL = 0  # 正常交易
    TRADE_STATUS_SUSPENDED = 1  # 停牌
    TRADE_STATUS_DELISTED = 2  # 退市

    # 订单类型
    ORDER_TYPE_LIMIT = 1  # 限价单
    ORDER_TYPE_MARKET = 2  # 市价单
    ORDER_TYPE_STOP_LOSS = 3  # 止损单
    ORDER_TYPE_STOP_PROFIT = 4  # 止盈单

    # 订单方向
    ORDER_SIDE_BUY = 1  # 买入
    ORDER_SIDE_SELL = 2  # 卖出

    # 订单状态
    ORDER_STATUS_PENDING = 0  # 待报
    ORDER_STATUS_SUBMITTED = 1  # 已报
    ORDER_STATUS_PARTIAL_FILLED = 2  # 部分成交
    ORDER_STATUS_FILLED = 3  # 全部成交
    ORDER_STATUS_CANCELLED = 4  # 已撤销
    ORDER_STATUS_REJECTED = 5  # 已拒绝
    ORDER_STATUS_EXPIRED = 6  # 已过期

    # 用户角色
    ROLE_SUPER_ADMIN = 'super_admin'  # 超级管理员
    ROLE_ADMIN = 'admin'  # 管理员
    ROLE_QUANT_RESEARCHER = 'quant_researcher'  # 量化研究员
    ROLE_TRADER = 'trader'  # 交易员
    ROLE_RISK_MANAGER = 'risk_manager'  # 风控经理
    ROLE_VIEWER = 'viewer'  # 查看者

    # 数据源
    DATA_SOURCE_TUSHARE = 'tushare'
    DATA_SOURCE_WIND = 'wind'
    DATA_SOURCE_JOINQUANT = 'joinquant'
    DATA_SOURCE_AKSHARE = 'akshare'
    DATA_SOURCE_EXCHANGE = 'exchange'

    # 数据粒度
    DATA_PERIOD_TICK = 'tick'
    DATA_PERIOD_1MIN = '1min'
    DATA_PERIOD_5MIN = '5min'
    DATA_PERIOD_15MIN = '15min'
    DATA_PERIOD_30MIN = '30min'
    DATA_PERIOD_60MIN = '60min'
    DATA_PERIOD_DAILY = 'daily'
    DATA_PERIOD_WEEKLY = 'weekly'
    DATA_PERIOD_MONTHLY = 'monthly'

    # 交易所
    EXCHANGE_SH = 'SH'
    EXCHANGE_SZ = 'SZ'
    EXCHANGE_BJ = 'BJ'

    # 板块
    BOARD_MAIN = '主板'
    BOARD_KCB = '科创板'
    BOARD_CYB = '创业板'
    BOARD_BJ = '北交所'

    # 行情推送频率
    MARKET_PUSH_INTERVAL_REALTIME = 1  # 实时行情推送间隔（秒）
    MARKET_PUSH_INTERVAL_MINUTE = 60  # 分钟行情推送间隔（秒）

    # 告警级别
    ALERT_LEVEL_INFO = 'info'
    ALERT_LEVEL_WARNING = 'warning'
    ALERT_LEVEL_ERROR = 'error'
    ALERT_LEVEL_CRITICAL = 'critical'

    # 告警渠道
    ALERT_CHANNEL_WECHAT = 'wechat'
    ALERT_CHANNEL_EMAIL = 'email'
    ALERT_CHANNEL_SMS = 'sms'
    ALERT_CHANNEL_PHONE = 'phone'

    # 回测状态
    BACKTEST_STATUS_PENDING = 0  # 排队中
    BACKTEST_STATUS_RUNNING = 1  # 运行中
    BACKTEST_STATUS_SUCCESS = 2  # 成功
    BACKTEST_STATUS_FAILED = 3  # 失败
    BACKTEST_STATUS_CANCELLED = 4  # 已取消

    # 策略状态
    STRATEGY_STATUS_DRAFT = 0  # 草稿
    STRATEGY_STATUS_TESTING = 1  # 测试中
    STRATEGY_STATUS_ONLINE = 2  # 已上线
    STRATEGY_STATUS_OFFLINE = 3  # 已下线

    # 模拟交易状态
    SIMULATION_STATUS_RUNNING = 0  # 运行中
    SIMULATION_STATUS_STOPPED = 1  # 已停止
    SIMULATION_STATUS_PAUSED = 2  # 已暂停

    # 风控规则级别
    RULE_LEVEL_WARNING = 'warning'  # 警告
    RULE_LEVEL_ERROR = 'error'  # 错误
    RULE_LEVEL_BLOCK = 'block'  # 阻断

    # 熔断级别
    CIRCUIT_BREAKER_LEVEL_NORMAL = 0  # 正常
    CIRCUIT_BREAKER_LEVEL1 = 1  # 一级熔断：禁止回测
    CIRCUIT_BREAKER_LEVEL2 = 2  # 二级熔断：禁止算法交易
    CIRCUIT_BREAKER_LEVEL3 = 3  # 三级熔断：禁止新开仓
    CIRCUIT_BREAKER_LEVEL4 = 4  # 四级熔断：禁止所有交易

    # 交易费用
    DEFAULT_COMMISSION_RATE = 0.0003  # 默认佣金费率万3
    DEFAULT_MIN_COMMISSION = 5.0  # 最低佣金5元
    DEFAULT_STAMP_DUTY_RATE = 0.001  # 印花税千1（卖出时收）
    DEFAULT_TRANSFER_FEE_RATE = 0.00001  # 过户费万0.1

    # 涨跌停限制
    PRICE_LIMIT_MAIN = 0.10  # 主板10%
    PRICE_LIMIT_KCB_CYB = 0.20  # 科创板/创业板20%
    PRICE_LIMIT_BJ = 0.30  # 北交所30%
    PRICE_LIMIT_ST = 0.05  # ST股5%

    # 持仓可用时间（T+1）
    POSITION_AVAILABLE_DELAY_DAYS = 1


class ErrorCode(Enum):
    """错误码枚举"""
    SUCCESS = 200, "操作成功"
    BAD_REQUEST = 400, "请求参数错误"
    UNAUTHORIZED = 401, "未认证或认证已过期"
    FORBIDDEN = 403, "没有权限访问该资源"
    NOT_FOUND = 404, "请求的资源不存在"
    TOO_MANY_REQUESTS = 429, "请求过于频繁，请稍后再试"
    INTERNAL_ERROR = 500, "服务器内部错误"
    SERVICE_UNAVAILABLE = 503, "服务暂时不可用"

    # 业务错误码 1000+
    INSUFFICIENT_FUNDS = 1001, "账户资金不足"
    INSUFFICIENT_POSITION = 1002, "持仓不足"
    ORDER_NOT_FOUND = 1003, "订单不存在"
    ORDER_CANNOT_CANCEL = 1004, "订单无法撤销"
    STOCK_SUSPENDED = 1005, "股票已停牌"
    PRICE_OUT_OF_LIMIT = 1006, "价格超出涨跌停限制"
    INVALID_STOCK_CODE = 1007, "无效的股票代码"
    STRATEGY_RUNTIME_ERROR = 1008, "策略运行错误"
    BACKTEST_FAILED = 1009, "回测执行失败"
    DATA_SOURCE_ERROR = 1010, "数据源访问错误"
    CIRCUIT_BREAKER_TRIGGERED = 1011, "系统熔断，交易功能暂时不可用"
    RISK_CHECK_FAILED = 1012, "风控检查不通过"
    DUPLICATE_REQUEST = 1013, "重复请求"
    SIGNATURE_VERIFICATION_FAILED = 1014, "签名验证失败"

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


__all__ = [
    'SystemConstants',
    'BusinessConstants',
    'ErrorCode',
    'DEFAULT_QUALITY_RULES'
]
