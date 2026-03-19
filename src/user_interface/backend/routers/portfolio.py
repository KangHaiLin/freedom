"""
投资组合/账户API路由
提供仪表盘总览数据
"""
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..dependencies import verify_api_key
from src.trading_engine.trading_manager import TradingManager
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from ..schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])

# 全局交易管理器实例
# 在应用启动时会初始化，这里保持单例
_trading_manager: Optional[TradingManager] = None


def get_trading_manager() -> TradingManager:
    """获取或创建交易管理器单例"""
    global _trading_manager
    if _trading_manager is None:
        # 默认初始资金100万
        _trading_manager = TradingManager(initial_cash=1000000.0)
    return _trading_manager


def set_trading_manager(tm: TradingManager) -> None:
    """设置交易管理器实例（应用启动时调用）"""
    global _trading_manager
    _trading_manager = tm


@router.get("/dashboard", summary="获取仪表盘总览数据", response_model=BaseResponse)
async def get_dashboard_data():
    """
    获取仪表盘完整数据，包括：
    - 账户汇总信息
    - 资产配置
    - 重仓持股列表
    - 权益曲线历史
    """
    tm = get_trading_manager()
    pm = tm.get_portfolio_manager()

    # 获取账户汇总
    summary = build_account_summary(pm)

    # 获取资产配置
    allocation = build_asset_allocation(pm)

    # 获取重仓持股（按市值排序取前N）
    top_holdings = get_top_holdings(pm, limit=5)

    # 获取权益曲线（这里暂时使用模拟数据，实际应该从历史记录获取）
    equity_curve = generate_mock_equity_curve(90)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "account_summary": summary,
            "asset_allocation": allocation,
            "top_holdings": top_holdings,
            "equity_curve": equity_curve,
        }
    }


@router.get("/summary", summary="获取账户汇总信息", response_model=BaseResponse)
async def get_account_summary():
    """获取账户汇总信息"""
    tm = get_trading_manager()
    pm = tm.get_portfolio_manager()
    summary = build_account_summary(pm)
    return {
        "code": 200,
        "message": "success",
        "data": summary
    }


@router.get("/asset-allocation", summary="获取资产配置数据", response_model=BaseResponse)
async def get_asset_allocation():
    """获取资产配置数据"""
    tm = get_trading_manager()
    pm = tm.get_portfolio_manager()
    allocation = build_asset_allocation(pm)
    return {
        "code": 200,
        "message": "success",
        "data": allocation
    }


@router.get("/top-holdings", summary="获取重仓持股列表", response_model=BaseResponse)
async def get_top_holdings_route(
    limit: int = Query(10, description="返回最大数量，默认10")):
    """获取按市值排序的重仓持股列表"""
    tm = get_trading_manager()
    pm = tm.get_portfolio_manager()
    holdings = get_top_holdings(pm, limit=limit)
    return {
        "code": 200,
        "message": "success",
        "data": holdings
    }


@router.get("/equity-curve", summary="获取权益曲线历史", response_model=BaseResponse)
async def get_equity_curve_route(
    days: int = Query(90, description="获取最近多少天，默认90")):
    """获取权益曲线历史数据"""
    # TODO: 实际应该从交易记录数据库中获取历史净值数据
    curve = generate_mock_equity_curve(days)
    return {
        "code": 200,
        "message": "success",
        "data": curve
    }


def build_account_summary(pm: PortfolioManager) -> dict:
    """从投资组合管理器构建账户汇总信息"""
    summary = pm.get_summary()
    total_asset = pm.get_total_asset()
    cash = pm.get_cash()
    initial_cash = pm.get_initial_cash()

    # 计算总收益率
    total_pnl = total_asset - initial_cash
    total_pnl_pct = total_pnl / initial_cash if initial_cash > 0 else 0

    # 今日收益（实际应该计算，这里从统计数据获取
    # 简化实现，实际应从每日结算数据计算
    daily_pnl = summary.get('daily_pnl', 0)
    daily_pnl_pct = daily_pnl / total_asset if total_asset > 0 else 0

    return {
        "initial_cash": initial_cash,
        "current_cash": cash,
        "total_asset": total_asset,
        "total_market_value": total_asset - cash,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "daily_pnl": daily_pnl,
        "daily_pnl_pct": daily_pnl_pct,
        "position_count": pm.get_position_count(),
    }


def build_asset_allocation(pm: PortfolioManager) -> List[dict]:
    """构建资产配置"""
    total_asset = pm.get_total_asset()
    cash = pm.get_cash()
    positions = pm.get_non_empty_positions()

    # 按行业分类汇总市值
    # 这里简单分类
    category_map = {
        "股票": 0,
        "现金": cash,
        "债券": 0,
        "其他": 0,
    }

    # 股票总市值
    total_mv = 0
    for pos in positions:
        mv = pos.get_market_value()
        total_mv += mv
        # 实际应该按行业分类，这里简化处理
    category_map["股票"] = total_mv

    # 计算百分比
    result = []
    colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]
    for i, (name, value) in enumerate(category_map.items()):
        if total_asset > 0:
            pct = round((value / total_asset * 100), 1)
        else:
            pct = 0
        result.append({
                "name": name,
                "value": pct,
                "color": colors[i % len(colors)]
            })

    # 过滤掉0值
    result = [item for item in result if item["value"] > 0]
    return result


def get_top_holdings(pm: PortfolioManager, limit: int = 10) -> List[dict]:
    """获取市值排序的前N个重仓持股"""
    positions = pm.get_non_empty_positions()

    # 按市值降序排序
    sorted_positions = sorted(
        positions,
        key=lambda p: p.get_market_value(),
        reverse=True
    )

    # 取前N个
    result = []
    for pos in sorted_positions[:limit]:
                result.append(pos.to_dict())

    return result


def generate_mock_equity_curve(days: int) -> List[dict]:
    """
    生成模拟权益曲线数据
    实际应用中应该从历史净值数据库读取
    """
    result = []
    tm = get_trading_manager()
    pm = tm.get_portfolio_manager()
    initial_value = pm.get_initial_cash()
    current_value = pm.get_total_asset()

    # 从initial_value到current_value生成一个增长曲线
    import random
    current = initial_value
    today = datetime.now()

    for i in range(min(days, 90)):
        date = today - timedelta(days=(90 - i - 1))
        date_str = date.strftime("%m/%d")
        # 随机波动增长
        daily_change = random.uniform(-0.02, 0.025)
        current = current * (1 + daily_change)
        # 最后一天用真实值
        if i == min(days, 90) - 1:
            current = current_value
        result.append({
            "date": date_str,
            "value": round(current, 2)
        })

    return result
