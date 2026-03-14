"""
行情数据API路由
"""
from fastapi import APIRouter, Query, Depends
from typing import List, Optional, Union
from datetime import date, datetime
import logging

from ..dependencies import verify_api_key
from ...data_management.data_query.query_manager import query_manager
from ..schemas import MarketDataResponse, RealtimeQuoteResponse, DailyQuoteResponse, MinuteQuoteResponse, TickQuoteResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/realtime", summary="获取实时行情", response_model=MarketDataResponse[List[RealtimeQuoteResponse]])
async def get_realtime_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表，例如：['000001.SZ', '600000.SH']"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表")
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
        "query_time": result.query_time
    }


@router.get("/daily", summary="获取日线行情", response_model=MarketDataResponse[List[DailyQuoteResponse]])
async def get_daily_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Union[date, str] = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段，例如：['-trade_date', 'stock_code']"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量")
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
        offset=offset
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time
    }


@router.get("/minute", summary="获取分钟线行情", response_model=MarketDataResponse[List[MinuteQuoteResponse]])
async def get_minute_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Union[date, str] = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: int = Query(1, description="分钟周期：1/5/15/30/60"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段"),
    limit: Optional[int] = Query(10000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量")
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
        offset=offset
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time
    }


@router.get("/tick", summary="获取Tick行情", response_model=MarketDataResponse[List[TickQuoteResponse]])
async def get_tick_quote(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    date: Union[date, str] = Query(..., description="日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段"),
    limit: Optional[int] = Query(100000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量")
):
    """
    获取股票Tick逐笔成交数据
    """
    result = query_manager.get_tick_quote(
        stock_codes=stock_codes,
        date=date,
        fields=fields,
        order_by=order_by,
        limit=limit,
        offset=offset
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time
    }


@router.get("/ma", summary="计算均线", response_model=MarketDataResponse[List[dict]])
async def calculate_ma(
    stock_code: str = Query(..., description="股票代码"),
    periods: List[int] = Query([5, 10, 20, 60], description="均线周期，例如：[5,10,20]"),
    days: int = Query(250, description="获取最近多少天的数据")
):
    """
    计算股票均线数据
    """
    result = query_manager.get_query_service('market').calculate_ma(stock_code, periods, days)
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time
    }
