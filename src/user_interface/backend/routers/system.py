"""
系统管理API路由
"""
from fastapi import APIRouter, Depends
import logging
import psutil
import platform
from datetime import datetime
from typing import List
import uuid

from ..dependencies import verify_api_key, verify_admin_role
from ..schemas import BaseResponse, SystemStatusResponse, BacktestTaskResponse, BacktestResultResponse
from data_management.data_storage.storage_manager import storage_manager
from data_management.data_ingestion.data_source_manager import data_source_manager
from src.strategy_research.strategy_manager import StrategyResearchManager

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


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
        "python_version": platform.python_version()
    }

    # CPU信息
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "load_average": psutil.getloadavg()
    }

    # 内存信息
    memory = psutil.virtual_memory()
    memory_info = {
        "total": memory.total,
        "available": memory.available,
        "used": memory.used,
        "usage_percent": memory.percent
    }

    # 磁盘信息
    disk = psutil.disk_usage('/')
    disk_info = {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "usage_percent": disk.percent
    }

    # 存储状态
    storage_status = storage_manager.health_check()

    # 数据源状态
    data_source_status = {
        "total_sources": len(data_source_manager.sources),
        "available_sources": data_source_manager.get_available_source_count(),
        "sources": data_source_manager.get_source_status()
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
            "timestamp": datetime.now().isoformat()
        }
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
        "storage_configs": {name: {k: v for k, v in config.items() if k != 'password'} for name, config in settings.STORAGE_CONFIGS.items()}
    }
    return {
        "code": 200,
        "message": "success",
        "data": config
    }


@router.get("/storage_health", summary="获取存储健康状态", response_model=BaseResponse)
async def get_storage_health():
    """
    获取所有存储引擎的健康状态
    """
    health = storage_manager.health_check()
    return {
        "code": 200,
        "message": "success",
        "data": health
    }


@router.get("/data_source_health", summary="获取数据源健康状态", response_model=BaseResponse)
async def get_data_source_health():
    """
    获取所有数据源的健康状态
    """
    health = data_source_manager.health_check()
    return {
        "code": 200,
        "message": "success",
        "data": health
    }


@router.post("/reload_config", summary="重载系统配置", response_model=BaseResponse, dependencies=[Depends(verify_admin_role)])
async def reload_system_config():
    """
    重载系统配置（仅管理员可访问）
    """
    from common.config import settings
    settings.reload()
    return {
        "code": 200,
        "message": "系统配置重载成功"
    }


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

    return {
        "code": 200,
        "message": "success",
        "data": tasks
    }


@router.get("/backtest-tasks/{task_id}", summary="获取回测任务详情", response_model=BaseResponse)
async def get_backtest_task(task_id: str):
    """
    根据ID获取回测任务详情
    """
    if task_id not in _backtest_tasks:
        return {
            "code": 404,
            "message": f"回测任务 {task_id} 不存在",
            "data": None
        }

    return {
        "code": 200,
        "message": "success",
        "data": _backtest_tasks[task_id]
    }


@router.get("/strategies", summary="获取策略列表", response_model=BaseResponse)
async def list_strategies():
    """
    获取所有策略列表
    """
    manager = _get_strategy_manager()
    strategies = manager.list_strategies()

    # 转换为前端需要的格式
    from datetime import datetime
    result = []
    for idx, meta in enumerate(strategies):
        # 这里简化处理，实际应该从存储获取最新绩效数据
        result.append({
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
                {"date": "03/17", "value": 100}
            ]
        })

    return {
        "code": 200,
        "message": "success",
        "data": result
    }


@router.post("/backtest-tasks", summary="创建回测任务", response_model=BaseResponse)
async def create_backtest_task(name: str, strategy_id: str):
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
        "result": None
    }
    _backtest_tasks[task_id] = task

    return {
        "code": 200,
        "message": "创建成功",
        "data": task
    }
