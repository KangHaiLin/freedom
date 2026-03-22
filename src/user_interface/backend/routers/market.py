"""
行情数据API路由
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Query

from data_management.data_query.query_manager import query_manager

from ..dependencies import verify_api_key
from ..schemas import (
    DailyQuoteResponse,
    MarketDataResponse,
    MinuteQuoteResponse,
    RealtimeQuoteResponse,
    TickQuoteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ========== 前端对接端点 - 保持与前端API路径一致 ==========


@router.get("/search", summary="搜索股票", response_model=MarketDataResponse)
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词（代码或名称）"),
    limit: int = Query(20, description="返回结果数量限制"),
):
    """
    根据关键词搜索股票（支持代码或名称）
    """
    # 使用基本面查询服务搜索股票基础信息
    result = query_manager.get_stock_basic(stock_codes=None, fields=["stock_code", "name", "exchange", "list_status"])

    # 在内存中按关键词过滤
    if not result.data.empty:
        df = result.to_df()
        # 模糊匹配代码或名称
        mask = df["stock_code"].str.contains(keyword, case=False) | df["name"].str.contains(keyword, case=False)
        filtered_df = df[mask].head(limit)
        result.data = filtered_df
        result.total = len(filtered_df)

    # 转换格式匹配前端期望 {code, name}
    data_list = result.to_dict()["data"]
    formatted_data = []
    for item in data_list:
        formatted_data.append(
            {"code": item.get("stock_code", ""), "name": item.get("name", ""), "exchange": item.get("exchange", "")}
        )

    return {
        "code": 200,
        "message": "success",
        "data": formatted_data,
        "items": formatted_data,  # 兼容分页格式
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/stocks", summary="获取股票列表", response_model=MarketDataResponse)
async def get_stock_list(page: int = Query(1, description="页码"), page_size: int = Query(100, description="每页数量")):
    """
    获取股票列表分页
    """
    offset = (page - 1) * page_size
    result = query_manager.get_stock_basic(stock_codes=None, fields=["stock_code", "name", "exchange", "list_status"])

    # 分页
    total = result.total
    if not result.data.empty:
        df = result.to_df()
        paginated_df = df.iloc[offset : offset + page_size] if hasattr(df, "iloc") else df
        result.data = paginated_df
        result.total = total

    # 转换格式
    data_list = result.to_dict()["data"]
    formatted_data = []
    for item in data_list:
        formatted_data.append(
            {"code": item.get("stock_code", ""), "name": item.get("name", ""), "exchange": item.get("exchange", "")}
        )

    return {
        "code": 200,
        "message": "success",
        "data": formatted_data,
        "items": formatted_data,
        "total": total,
        "query_time": result.query_time,
    }


@router.get("/kline/daily", summary="获取日K线数据", response_model=MarketDataResponse)
async def get_daily_kline(
    code: str = Query(..., description="股票代码"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYYMMDD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYYMMDD"),
):
    """
    获取单只股票日K线数据（前端对接端点）
    """
    # 转换日期格式，如果是YYYYMMDD格式字符串
    if isinstance(start_date, str) and len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    if isinstance(end_date, str) and len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

    result = query_manager.get_daily_quote(
        stock_codes=[code],
        start_date=start_date or "1990-01-01",
        end_date=end_date,
        fields=["trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change"],
    )

    # 转换为前端期望的格式
    data = result.to_dict()["data"]

    return {"code": 200, "message": "success", "data": data, "total": result.total, "query_time": result.query_time}


@router.get("/kline/minute", summary="获取分钟K线数据", response_model=MarketDataResponse)
async def get_minute_kline(
    code: str = Query(..., description="股票代码"),
    freq: str = Query("1", description="分钟周期：1/5/15/30/60"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYYMMDD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYYMMDD"),
):
    """
    获取单只股票分钟K线数据（前端对接端点）
    """
    # 转换日期格式，如果是YYYYMMDD格式字符串
    if isinstance(start_date, str) and len(start_date) == 8:
        start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    if isinstance(end_date, str) and len(end_date) == 8:
        end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

    # 转换freq为period整数
    period = int(freq.replace("m", "")) if "m" in freq else int(freq)

    result = query_manager.get_minute_quote(
        stock_codes=[code],
        start_date=start_date or "1990-01-01",
        end_date=end_date,
        period=period,
        fields=["trade_time", "open", "high", "low", "close", "volume", "amount"],
    )

    # 转换为前端期望的格式
    data = result.to_dict()["data"]

    return {"code": 200, "message": "success", "data": data, "total": result.total, "query_time": result.query_time}


@router.get("/quotes", summary="获取多股票实时行情", response_model=MarketDataResponse)
async def get_realtime_quotes(codes: str = Query(..., description="股票代码列表，逗号分隔")):
    """
    获取多只股票实时行情（前端对接端点）
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    result = query_manager.get_realtime_quote(stock_codes=code_list)

    data = result.to_dict()["data"]

    return {"code": 200, "message": "success", "data": data, "total": result.total, "query_time": result.query_time}


@router.get("/quote/{code}", summary="获取单股票实时行情", response_model=MarketDataResponse)
async def get_realtime_quote_by_code(code: str):
    """
    获取单只股票实时行情（前端对接端点）
    """
    result = query_manager.get_realtime_quote(stock_codes=[code])

    data = result.to_dict()["data"]
    single_data = data[0] if data else None

    return {
        "code": 200,
        "message": "success",
        "data": single_data,
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/realtime", summary="获取实时行情", response_model=MarketDataResponse)
async def get_realtime_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表，例如：['000001.SZ', '600000.SH']"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
):
    """
    获取股票实时行情数据
    """
    result = query_manager.get_realtime_quote(stock_codes, fields)
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/daily", summary="获取日线行情", response_model=MarketDataResponse)
async def get_daily_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Union[date, str] = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段，例如：['-trade_date', 'stock_code']"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票日线行情数据
    """
    result = query_manager.get_daily_quote(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        fields=fields,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/minute", summary="获取分钟线行情", response_model=MarketDataResponse)
async def get_minute_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Union[date, str] = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: int = Query(1, description="分钟周期：1/5/15/30/60"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段"),
    limit: Optional[int] = Query(10000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票分钟线行情数据
    """
    result = query_manager.get_minute_quote(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        period=period,
        fields=fields,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/tick", summary="获取Tick行情", response_model=MarketDataResponse)
async def get_tick_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    date: Union[date, str] = Query(..., description="日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段"),
    limit: Optional[int] = Query(100000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票Tick逐笔成交数据
    """
    result = query_manager.get_tick_quote(
        stock_codes=stock_codes, date=date, fields=fields, order_by=order_by, limit=limit, offset=offset
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/ma", summary="计算均线", response_model=MarketDataResponse)
async def calculate_ma(
    stock_code: str = Query(..., description="股票代码"),
    periods: List[int] = Query([5, 10, 20, 60], description="均线周期，例如：[5,10,20]"),
    days: int = Query(250, description="获取最近多少天的数据"),
):
    """
    计算股票均线数据
    """
    result = query_manager.get_query_service("market").calculate_ma(stock_code, periods, days)
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }
