"""
基本面数据API路由
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Query

from data_management.data_query.query_manager import query_manager

from ..dependencies import verify_api_key
from ..schemas import (
    BalanceSheetResponse,
    CashFlowResponse,
    DividendResponse,
    FinancialIndicatorResponse,
    HolderInfoResponse,
    IncomeStatementResponse,
    MarketDataResponse,
    StockBasicResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/stock_basic", summary="获取股票基础信息", response_model=MarketDataResponse)
async def get_stock_basic(
    stock_codes: Optional[List[str]] = Query(None, description="股票代码列表，为空则返回所有股票"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    list_status: Optional[str] = Query(None, description="上市状态：L上市/D退市/P暂停上市"),
    exchange: Optional[str] = Query(None, description="交易所：SSE上交所/SZSE深交所/BJSE北交所"),
):
    """
    获取股票基础信息列表
    """
    filters = {}
    if list_status:
        filters["list_status"] = list_status
    if exchange:
        filters["exchange"] = exchange

    result = query_manager.get_stock_basic(stock_codes=stock_codes, fields=fields, **filters)
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }


@router.get("/financial_indicator", summary="获取财务指标", response_model=MarketDataResponse)
async def get_financial_indicator(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    order_by: Optional[List[str]] = Query(None, description="排序字段"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票财务指标数据
    """
    result = query_manager.get_financial_indicator(
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


@router.get("/income_statement", summary="获取利润表", response_model=MarketDataResponse)
async def get_income_statement(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    report_type: Optional[str] = Query(None, description="报告类型：Q1/Q2/Q3/Q4/ALL"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票利润表数据
    """
    result = query_manager.get_income_statement(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        fields=fields,
        report_type=report_type,
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


@router.get("/balance_sheet", summary="获取资产负债表", response_model=MarketDataResponse)
async def get_balance_sheet(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    report_type: Optional[str] = Query(None, description="报告类型：Q1/Q2/Q3/Q4/ALL"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票资产负债表数据
    """
    result = query_manager.get_balance_sheet(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        fields=fields,
        report_type=report_type,
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


@router.get("/cash_flow", summary="获取现金流量表", response_model=MarketDataResponse)
async def get_cash_flow(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    report_type: Optional[str] = Query(None, description="报告类型：Q1/Q2/Q3/Q4/ALL"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票现金流量表数据
    """
    result = query_manager.get_cash_flow(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        fields=fields,
        report_type=report_type,
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


@router.get("/holder_info", summary="获取股东信息", response_model=MarketDataResponse)
async def get_holder_info(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    holder_type: Optional[str] = Query(None, description="股东类型：top10/top10_flow/manager"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票股东信息
    """
    result = query_manager.get_holder_info(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        holder_type=holder_type,
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


@router.get("/dividend", summary="获取分红送股信息", response_model=MarketDataResponse)
async def get_dividend(
    stock_codes: List[str] = Query(..., description="股票代码列表"),
    start_date: Optional[Union[date, str]] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[Union[date, str]] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    fields: Optional[List[str]] = Query(None, description="需要返回的字段列表"),
    limit: Optional[int] = Query(1000, description="返回记录数限制"),
    offset: Optional[int] = Query(0, description="偏移量"),
):
    """
    获取股票分红送股信息
    """
    result = query_manager.get_dividend(
        stock_codes=stock_codes, start_date=start_date, end_date=end_date, fields=fields, limit=limit, offset=offset
    )
    return {
        "code": 200,
        "message": "success",
        "data": result.to_dict()["data"],
        "total": result.total,
        "query_time": result.query_time,
    }
