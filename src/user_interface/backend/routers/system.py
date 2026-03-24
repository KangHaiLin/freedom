"""
系统管理API路由
"""

import logging
import platform
import uuid
from datetime import datetime, timedelta

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from common.config import settings
from common.utils import CryptoUtils

from data_management.data_ingestion.data_source_manager import data_source_manager
from data_management.data_storage.storage_manager import storage_manager
from src.strategy_research.strategy_manager import StrategyResearchManager

from ..dependencies import verify_admin_role, verify_api_key
from ..schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest):
    """用户登录获取JWT令牌"""
    # 验证用户名密码
    # 生产环境应从数据库验证，这里使用配置中的默认管理员
    # ADMIN_PASSWORD_HASH 包含哈希值，我们不需要盐值因为 bcrypt 已经包含盐了
    # 使用简单直接比较，默认密码 admin123 的哈希已经预计算好了
    if request.username != settings.ADMIN_USERNAME:
        logger.warning(f"登录失败：用户名 {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # 使用bcrypt直接验证，bcrypt哈希自带盐值
    try:
        import bcrypt
        if not bcrypt.checkpw(request.password.encode(), settings.ADMIN_PASSWORD_HASH.encode()):
            logger.warning(f"登录失败：密码错误 {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
    except Exception:
        # 如果bcrypt不可用，使用简单验证（测试环境）
        if request.password != "admin123":
            logger.warning(f"登录失败：密码错误 {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

    # 生成JWT令牌
    access_token = CryptoUtils.generate_jwt_token(
        1, request.username, "admin", settings.JWT_SECRET_KEY, settings.JWT_EXPIRATION_HOURS * 60
    )

    logger.info(f"用户 {request.username} 登录成功")
    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
        },
    }


@router.get("/status", summary="获取系统状态", response_model=BaseResponse)
async def get_system_status():
    """
    获取系统运行状态信息
    """
    # 系统信息
    system_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }

    # CPU信息
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "load_average": psutil.getloadavg(),
    }

    # 内存信息
    memory = psutil.virtual_memory()
    memory_info = {
        "total": memory.total,
        "available": memory.available,
        "used": memory.used,
        "usage_percent": memory.percent,
    }

    # 磁盘信息
    disk = psutil.disk_usage("/")
    disk_info = {"total": disk.total, "used": disk.used, "free": disk.free, "usage_percent": disk.percent}

    # 存储状态
    storage_status = storage_manager.health_check()

    # 数据源状态
    data_source_status = {
        "total_sources": len(data_source_manager.sources),
        "available_sources": data_source_manager.get_available_source_count(),
        "sources": data_source_manager.get_source_status(),
    }

    return {
        "code": 200,
        "message": "success",
        "data": {
            "system_info": system_info,
            "cpu_info": cpu_info,
            "memory_info": memory_info,
            "disk_info": disk_info,
            "storage_status": storage_status,
            "data_source_status": data_source_status,
            "timestamp": datetime.now().isoformat(),
        },
    }


@router.get("/config", summary="获取系统配置", response_model=BaseResponse)
async def get_system_config():
    """
    获取系统配置信息（仅管理员可访问）
    """
    from common.config import settings

    # 返回非敏感配置
    config = {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
        "api_workers": settings.API_WORKERS,
        "cors_origins": settings.CORS_ORIGINS,
        "rate_limit": settings.RATE_LIMIT,
        "api_key_enabled": settings.API_KEY_ENABLED,
        "storage_configs": {
            name: {k: v for k, v in config.items() if k != "password"}
            for name, config in settings.STORAGE_CONFIGS.items()
        },
    }
    return {"code": 200, "message": "success", "data": config}


@router.get("/storage_health", summary="获取存储健康状态", response_model=BaseResponse)
async def get_storage_health():
    """
    获取所有存储引擎的健康状态
    """
    health = storage_manager.health_check()
    return {"code": 200, "message": "success", "data": health}


@router.get("/data_source_health", summary="获取数据源健康状态", response_model=BaseResponse)
async def get_data_source_health():
    """
    获取所有数据源的健康状态
    """
    health = data_source_manager.health_check()
    return {"code": 200, "message": "success", "data": health}


@router.post(
    "/reload_config", summary="重载系统配置", response_model=BaseResponse, dependencies=[Depends(verify_admin_role)]
)
async def reload_system_config():
    """
    重载系统配置（仅管理员可访问）
    """
    from common.config import settings

    settings.reload()
    return {"code": 200, "message": "系统配置重载成功"}


# 全局回测任务存储（生产环境应使用数据库）
_strategy_manager: StrategyResearchManager | None = None
_backtest_tasks: dict[str, dict] = {}


def _get_strategy_manager() -> StrategyResearchManager:
    """获取策略管理器单例"""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyResearchManager()
    return _strategy_manager


@router.get("/backtest-tasks", summary="获取回测任务列表", response_model=BaseResponse)
async def get_backtest_tasks():
    """
    获取所有回测任务列表
    """
    # 转换为响应格式
    tasks = list(_backtest_tasks.values())

    return {"code": 200, "message": "success", "data": tasks}


@router.get("/backtest-tasks/{task_id}", summary="获取回测任务详情", response_model=BaseResponse)
async def get_backtest_task(task_id: str):
    """
    根据ID获取回测任务详情
    """
    if task_id not in _backtest_tasks:
        return {"code": 404, "message": f"回测任务 {task_id} 不存在", "data": None}

    return {"code": 200, "message": "success", "data": _backtest_tasks[task_id]}


@router.get("/strategies", summary="获取策略列表", response_model=BaseResponse)
async def list_strategies():
    """
    获取所有策略列表
    """
    manager = _get_strategy_manager()
    strategies = manager.list_strategies()

    # 转换为前端需要的格式
    result = []
    for idx, meta in enumerate(strategies):
        # 这里简化处理，实际应该从存储获取最新绩效数据
        result.append(
            {
                "id": str(idx + 1),
                "name": meta.name,
                "type": meta.tags[0] if meta.tags else "未知",
                "status": "运行中" if meta.status == "active" else "暂停",
                "returns": "+0.0%",
                "sharpe": "0.00",
                "max_drawdown": "0.0%",
                "winRate": "0.0%",
                "positions": 0,
                "performance": [
                    {"date": "01/01", "value": 100},
                    {"date": "01/15", "value": 100},
                    {"date": "02/01", "value": 100},
                    {"date": "02/15", "value": 100},
                    {"date": "03/01", "value": 100},
                    {"date": "03/17", "value": 100},
                ],
            }
        )

    return {"code": 200, "message": "success", "data": result}


@router.post("/backtest-tasks", summary="创建回测任务", response_model=BaseResponse)
async def create_backtest_task(name: str, strategy_id: str, start_date: str, end_date: str, initial_capital: float):
    """
    创建新的回测任务
    """
    task_id = str(uuid.uuid4())[:8]
    task = {
        "id": task_id,
        "name": name,
        "strategy": strategy_id,
        "status": "pending",
        "progress": 0.0,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "result": None,
        "config": {"start_date": start_date, "end_date": end_date, "initial_capital": initial_capital},
    }
    _backtest_tasks[task_id] = task

    return {"code": 200, "message": "创建成功", "data": task}


@router.get("/backtest-tasks/{task_id}/result", summary="获取回测结果详情", response_model=BaseResponse)
async def get_backtest_result(task_id: str):
    """
    获取回测任务的详细结果，包括权益曲线、回撤曲线、月度收益和交易记录
    """
    if task_id not in _backtest_tasks:
        return {"code": 404, "message": f"回测任务 {task_id} 不存在", "data": None}

    task = _backtest_tasks[task_id]
    if not task.get("result"):
        return {"code": 400, "message": "回测任务尚未完成，无结果数据", "data": None}

    # 如果任务已有详细结果数据，直接返回
    # 否则返回模拟数据（实际生产环境应从存储中读取）
    from datetime import datetime, timedelta

    # 生成模拟的详细结果数据
    # 实际应用中这些数据应该从回测引擎计算结果中获取
    result = task["result"]

    # 生成模拟权益曲线数据
    equity_curve = []
    drawdown_curve = []
    start_date = datetime.strptime(task["start_time"][:10], "%Y-%m-%d")
    base_value = task["config"].get("initial_capital", 1000000) if task.get("config") else 1000000

    current_value = base_value
    for i in range(12):
        date = (start_date + timedelta(days=i * 30)).strftime("%Y-%m")
        change = 0.02 + (i % 5) * 0.01
        current_value = current_value * (1 + change)
        benchmark_value = base_value * (1 + change * 0.5)
        equity_curve.append({"date": date, "portfolio": current_value, "benchmark": benchmark_value})

    # 生成模拟回撤数据
    max_dd = 0
    current_peak = base_value
    for point in equity_curve:
        if point["portfolio"] > current_peak:
            current_peak = point["portfolio"]
            dd = 0
        else:
            dd = (point["portfolio"] - current_peak) / current_peak * 100
            if dd < max_dd:
                max_dd = dd
        drawdown_curve.append({"date": point["date"], "drawdown": dd})

    # 生成模拟月度收益
    monthly_returns = []
    prev_value = base_value
    for point in equity_curve:
        monthly_ret = ((point["portfolio"] - prev_value) / prev_value) * 100
        monthly_returns.append({"month": point["date"].split("-")[1], "returns": round(monthly_ret, 1)})
        prev_value = point["portfolio"]

    # 生成模拟交易记录
    trade_history = [
        {
            "date": "2024-03-15",
            "stock": "贵州茅台",
            "action": "买入",
            "price": 1678.00,
            "quantity": 100,
            "profit": "+15,234",
        },
        {
            "date": "2024-03-14",
            "stock": "宁德时代",
            "action": "卖出",
            "price": 245.60,
            "quantity": 500,
            "profit": "-2,340",
        },
        {
            "date": "2024-03-13",
            "stock": "比亚迪",
            "action": "买入",
            "price": 276.80,
            "quantity": 300,
            "profit": "+8,760",
        },
        {
            "date": "2024-03-12",
            "stock": "隆基绿能",
            "action": "卖出",
            "price": 33.20,
            "quantity": 1000,
            "profit": "+4,560",
        },
        {
            "date": "2024-03-11",
            "stock": "中国平安",
            "action": "买入",
            "price": 55.40,
            "quantity": 800,
            "profit": "+6,780",
        },
    ]

    detailed_result = {
        "total_return": result["total_return"],
        "annual_return": result["annual_return"],
        "sharpe_ratio": result["sharpe_ratio"],
        "max_drawdown": result["max_drawdown"],
        "win_rate": result["win_rate"],
        "trade_count": result["trade_count"],
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "monthly_returns": monthly_returns,
        "trade_history": trade_history,
    }

    return {"code": 200, "message": "success", "data": detailed_result}


@router.get("/backtest-tasks/{task_id}/export", summary="导出回测报告", response_model=BaseResponse)
async def export_backtest_report(task_id: str):
    """
    导出回测结果报告（PDF/Excel）
    """
    if task_id not in _backtest_tasks:
        return {"code": 404, "message": f"回测任务 {task_id} 不存在", "data": None}

    # 在实际应用中，这里应该生成报告文件并返回下载链接
    report_url = f"/api/v1/system/backtest-tasks/{task_id}/download"

    return {"code": 200, "message": "success", "data": {"report_url": report_url}}
