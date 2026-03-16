"""
FastAPI主程序
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from datetime import datetime
from pathlib import Path

from common.config import settings
from common.exceptions import BaseAppException
from .middleware import RequestLogMiddleware, RateLimitMiddleware
from .routers import market, fundamental, monitor, system
from .websocket import ws_router

logger = logging.getLogger(__name__)

# 创建FastAPI实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A股量化交易系统API接口",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加中间件
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimitMiddleware)

# 注册路由
app.include_router(market.router, prefix="/api/v1/market", tags=["行情数据"])
app.include_router(fundamental.router, prefix="/api/v1/fundamental", tags=["基本面数据"])
app.include_router(monitor.router, prefix="/api/v1/monitor", tags=["监控管理"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(ws_router)

# 挂载前端静态文件（生产模式）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

# 全局异常处理
@app.exception_handler(BaseAppException)
async def base_app_exception_handler(request: Request, exc: BaseAppException):
    """自定义业务异常处理"""
    logger.error(f"请求异常：{request.method} {request.url}，错误：{exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", ""),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"请求异常：{request.method} {request.url}，错误：{str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "details": str(exc) if settings.DEBUG else None,
            "request_id": getattr(request.state, "request_id", ""),
            "timestamp": datetime.now().isoformat()
        }
    )

# 根路由
@app.get("/", tags=["根路径"])
async def root():
    return {
        "code": 200,
        "message": "A股量化交易系统API服务",
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "timestamp": datetime.now().isoformat()
    }

# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {
        "code": 200,
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=settings.API_WORKERS
    )
