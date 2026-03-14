"""
监控管理API路由
"""
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from datetime import datetime
import logging

from ..dependencies import verify_api_key, verify_admin_role
from ...data_management.data_monitoring.monitor_manager import monitor_manager
from ..schemas import BaseResponse, MonitorStatusResponse, AlertRecordResponse, DashboardResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/status", summary="获取监控状态", response_model=BaseResponse[List[MonitorStatusResponse]])
async def get_monitor_status():
    """
    获取所有监控任务的运行状态
    """
    status = monitor_manager.get_monitor_status()
    return {
        "code": 200,
        "message": "success",
        "data": status
    }


@router.get("/dashboard", summary="获取监控面板数据", response_model=BaseResponse[DashboardResponse])
async def get_monitor_dashboard():
    """
    获取监控面板统计数据
    """
    data = monitor_manager.get_dashboard_data()
    return {
        "code": 200,
        "message": "success",
        "data": data
    }


@router.get("/alerts", summary="获取历史告警记录", response_model=BaseResponse[List[AlertRecordResponse]])
async def get_recent_alerts(
    limit: int = Query(100, description="返回记录数限制"),
    level: Optional[str] = Query(None, description="告警级别：info/warning/error/critical"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间")
):
    """
    查询历史告警记录
    """
    alerts = monitor_manager.get_recent_alerts(limit, level, start_time, end_time)
    return {
        "code": 200,
        "message": "success",
        "data": alerts,
        "total": len(alerts)
    }


@router.post("/run_all", summary="立即执行所有监控", response_model=BaseResponse[List[dict]], dependencies=[Depends(verify_admin_role)])
async def run_all_monitors():
    """
    立即执行所有监控检查，返回检查结果
    """
    results = monitor_manager.run_all_once()
    return {
        "code": 200,
        "message": "success",
        "data": [r.to_dict() for r in results]
    }


@router.post("/start", summary="启动监控调度器", response_model=BaseResponse, dependencies=[Depends(verify_admin_role)])
async def start_monitor():
    """
    启动监控定时调度器
    """
    if monitor_manager.running:
        return {
            "code": 400,
            "message": "监控调度器已经在运行中"
        }
    monitor_manager.start()
    return {
        "code": 200,
        "message": "监控调度器启动成功"
    }


@router.post("/stop", summary="停止监控调度器", response_model=BaseResponse, dependencies=[Depends(verify_admin_role)])
async def stop_monitor():
    """
    停止监控定时调度器
    """
    if not monitor_manager.running:
        return {
            "code": 400,
            "message": "监控调度器已经停止"
        }
    monitor_manager.stop()
    return {
        "code": 200,
        "message": "监控调度器停止成功"
    }


@router.post("/clear_cache", summary="清除查询缓存", response_model=BaseResponse, dependencies=[Depends(verify_admin_role)])
async def clear_query_cache(
    pattern: Optional[str] = Query(None, description="缓存键匹配模式，为空则清除所有查询缓存")
):
    """
    清除数据查询缓存
    """
    from ...data_management.data_query.query_manager import query_manager
    deleted_count = query_manager.clear_cache(pattern)
    return {
        "code": 200,
        "message": f"成功清除{deleted_count}条缓存"
    }


@router.get("/health", summary="监控服务健康检查", response_model=BaseResponse)
async def monitor_health_check():
    """
    检查监控服务健康状态
    """
    health = monitor_manager.health_check()
    return {
        "code": 200,
        "message": "success",
        "data": health
    }
