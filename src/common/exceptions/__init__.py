"""
公共异常定义
所有业务异常都继承自BaseAppException
"""
from typing import Optional, Dict


class BaseAppException(Exception):
    """应用基础异常类"""
    code: int = 500
    message: str = "服务器内部错误"
    details: Optional[Dict] = None

    def __init__(
        self,
        message: str = None,
        code: int = None,
        details: Optional[Dict] = None
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "error_type": self.__class__.__name__
        }


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


# 数据源异常
class DataSourceException(BaseAppException):
    code = 500
    message = "数据源访问异常"


# 数据验证异常
class DataValidationException(BaseAppException):
    code = 400
    message = "数据验证失败"


# 存储异常
class StorageException(BaseAppException):
    code = 500
    message = "数据存储异常"


# 查询异常
class QueryException(BaseAppException):
    code = 500
    message = "数据查询异常"


# 策略运行异常
class StrategyRuntimeException(BaseAppException):
    code = 500
    message = "策略运行异常"


# 订单异常
class OrderException(BaseAppException):
    code = 400
    message = "订单处理异常"


# 资金不足异常
class InsufficientFundsException(BaseAppException):
    code = 400
    message = "账户资金不足"


# 持仓不足异常
class InsufficientPositionException(BaseAppException):
    code = 400
    message = "持仓不足"


# 熔断触发异常
class CircuitBreakerException(BaseAppException):
    code = 503
    message = "系统熔断，交易功能暂时不可用"
