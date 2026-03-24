"""
API中间件
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from common.config import settings
from common.utils import DateTimeUtils
from data_management.data_storage.storage_manager import storage_manager

logger = logging.getLogger(__name__)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        # 记录请求开始日志
        logger.info(
            f"[{request_id}] 请求开始：{request.method} {request.url.path} "
            f"客户端IP：{request.client.host} "
            f"用户代理：{request.headers.get('user-agent', '')}"
        )

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

            # 记录请求结束日志
            logger.info(
                f"[{request_id}] 请求结束：{request.method} {request.url.path} "
                f"状态码：{response.status_code} "
                f"耗时：{process_time:.2f}ms"
            )

            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] 请求异常：{request.method} {request.url.path} "
                f"错误：{str(e)} "
                f"耗时：{process_time:.2f}ms",
                exc_info=True,
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从settings读取当前配置，支持测试中patch修改
        rate_limit = settings.RATE_LIMIT

        # 延迟初始化redis
        if self.redis is None and settings.REDIS_CONFIG:
            self.redis = storage_manager.get_storage_by_type("redis")

        # 如果没有配置Redis或者限流关闭，直接放行
        if not self.redis or not rate_limit or rate_limit <= 0:
            return await call_next(request)

        # 跳过非API请求
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host
        current_minute = DateTimeUtils.now().strftime("%Y%m%d%H%M")
        key = f"rate_limit:{client_ip}:{current_minute}"

        try:
            # 计数
            current = self.redis.execute_sql(f"INCR {key}")
            if current == 1:
                self.redis.execute_sql(f"EXPIRE {key} 60")

            if current > rate_limit:
                logger.warning(f"客户端{client_ip}请求频率超限：{current}次/分钟")
                return Response(
                    content='{"code": 429, "message": "请求频率过高，请稍后再试"}',
                    status_code=429,
                    media_type="application/json",
                )

        except Exception as e:
            logger.error(f"限流检查失败：{e}")
            # 限流检查失败不影响正常请求
            pass

        return await call_next(request)
