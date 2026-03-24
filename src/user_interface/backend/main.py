"""
FastAPI主程序
"""

import os
import sys

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

import logging
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# 初始化日志配置
from common.config import settings

# 确保日志目录存在
log_path = Path(settings.log_path)
log_path.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(log_path / "app.log", encoding="utf-8"),  # 输出到文件
    ],
)

from common.config import settings
from common.exceptions import BaseAppException
from data_management.data_ingestion import init_all_data_sources, register_sync_tasks_to_scheduler
from system_management.task_scheduler.scheduler_manager import get_scheduler_manager

from .middleware import RateLimitMiddleware, RequestLogMiddleware
from .routers import fundamental, market, monitor, portfolio, system
from .websocket import ws_router

logger = logging.getLogger(__name__)

# 创建FastAPI实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A股量化交易系统API接口",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# 应用启动事件：初始化所有数据源
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据源"""
    logger.info("应用启动，开始初始化数据源...")
    init_all_data_sources()
    logger.info("数据源初始化完成")

    # 初始化调度器并注册数据同步任务
    logger.info("初始化任务调度器，注册数据同步任务...")
    scheduler = get_scheduler_manager()
    if not scheduler.is_running:
        # 从配置读取最大并发异步任务数
        max_concurrent = settings.SYSTEM_CONFIG.get("max_concurrent_async_tasks", 10)
        scheduler.initialize(max_concurrent_async=max_concurrent)
        scheduler.start()
    # 注册同步任务
    register_sync_tasks_to_scheduler()
    logger.info("数据同步任务注册完成")

    # 应用启动后，自动检测是否需要第一次全量同步
    # 如果daily_market_data表为空，说明是第一次运行，立即异步启动全量同步
    if settings.enable_daily_sync:
        logger.info("检测是否需要第一次全量同步...")

        def check_and_trigger_initial_sync():
            from data_management.data_ingestion import trigger_manual_sync

            try:
                result = trigger_manual_sync("daily")
                if result.get("success"):
                    logger.info(
                        f"初始全量同步完成: {result.get('message', '')}，共写入{result.get('total_records', 0)}条记录"
                    )
                else:
                    logger.error(f"初始全量同步失败: {result.get('message', '')}")
            except Exception as e:
                logger.error(f"初始全量同步执行异常: {e}", exc_info=True)

        # 提交为异步任务，不阻塞应用启动
        scheduler.submit_async(check_and_trigger_initial_sync, task_name="初始日线全量同步")
        logger.info("已提交初始全量同步任务到异步队列")


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

# 根路由
@app.get("/", tags=["根路径"])
async def root():
    return {
        "code": 200,
        "message": "A股量化交易系统API服务",
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "timestamp": datetime.now().isoformat(),
    }


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"code": 200, "status": "healthy", "timestamp": datetime.now().isoformat()}

# 注册路由
app.include_router(market.router, prefix="/api/v1/market", tags=["行情数据"])
app.include_router(fundamental.router, prefix="/api/v1/fundamental", tags=["基本面数据"])
app.include_router(monitor.router, prefix="/api/v1/monitor", tags=["监控管理"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["投资组合"])
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
            "timestamp": datetime.now().isoformat(),
        },
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
            "timestamp": datetime.now().isoformat(),
        },
    )


if __name__ == "__main__":
    if settings.debug:
        # 调试模式下使用reload需要传入字符串模块路径
        uvicorn.run(
            "src.user_interface.backend.main:app", host=settings.host, port=settings.port, reload=True, workers=1
        )
    else:
        # 生产模式直接传入app
        uvicorn.run(app, host=settings.host, port=settings.port, reload=False, workers=1)

# flake8: noqa: E402
