"""
API响应模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from datetime import datetime, date


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(200, description="响应码")
    message: str = Field("success", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    total: Optional[int] = Field(None, description="总记录数")
    query_time: Optional[float] = Field(None, description="查询耗时（秒）")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="响应时间")


class MarketDataResponse(BaseResponse):
    """行情数据响应模型"""
    data: Optional[List[Any]] = Field(None, description="数据列表")


# 行情数据模型
class RealtimeQuoteResponse(BaseModel):
    """实时行情响应模型"""
    stock_code: str = Field(..., description="股票代码")
    time: datetime = Field(..., description="行情时间")
    price: float = Field(..., description="当前价格")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    volume: Optional[int] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    bid_price1: Optional[float] = Field(None, description="买一价")
    bid_volume1: Optional[int] = Field(None, description="买一量")
    ask_price1: Optional[float] = Field(None, description="卖一价")
    ask_volume1: Optional[int] = Field(None, description="卖一量")
    source: Optional[str] = Field(None, description="数据来源")


class DailyQuoteResponse(BaseModel):
    """日线行情响应模型"""
    stock_code: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: Optional[int] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    adjust_factor: Optional[float] = Field(None, description="复权因子")


class MinuteQuoteResponse(BaseModel):
    """分钟线行情响应模型"""
    stock_code: str = Field(..., description="股票代码")
    trade_time: datetime = Field(..., description="交易时间")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: Optional[int] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")


class TickQuoteResponse(BaseModel):
    """Tick行情响应模型"""
    stock_code: str = Field(..., description="股票代码")
    trade_time: datetime = Field(..., description="交易时间")
    price: float = Field(..., description="成交价格")
    volume: Optional[int] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    bid_price1: Optional[float] = Field(None, description="买一价")
    bid_volume1: Optional[int] = Field(None, description="买一量")
    ask_price1: Optional[float] = Field(None, description="卖一价")
    ask_volume1: Optional[int] = Field(None, description="卖一量")


# 基本面数据模型
class StockBasicResponse(BaseModel):
    """股票基础信息响应模型"""
    stock_code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    exchange: Optional[str] = Field(None, description="交易所")
    list_date: Optional[date] = Field(None, description="上市日期")
    list_status: Optional[str] = Field(None, description="上市状态")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="市场板块")


class FinancialIndicatorResponse(BaseModel):
    """财务指标响应模型"""
    stock_code: str = Field(..., description="股票代码")
    report_date: date = Field(..., description="报告期")
    eps: Optional[float] = Field(None, description="每股收益")
    roe: Optional[float] = Field(None, description="净资产收益率")
    roa: Optional[float] = Field(None, description="总资产收益率")
    gross_margin: Optional[float] = Field(None, description="毛利率")
    net_margin: Optional[float] = Field(None, description="净利率")
    revenue: Optional[float] = Field(None, description="营业收入")
    net_profit: Optional[float] = Field(None, description="净利润")
    total_assets: Optional[float] = Field(None, description="总资产")
    total_liability: Optional[float] = Field(None, description="总负债")


class IncomeStatementResponse(BaseModel):
    """利润表响应模型"""
    stock_code: str = Field(..., description="股票代码")
    report_date: date = Field(..., description="报告期")
    report_type: Optional[str] = Field(None, description="报告类型")
    revenue: Optional[float] = Field(None, description="营业收入")
    operating_profit: Optional[float] = Field(None, description="营业利润")
    net_profit: Optional[float] = Field(None, description="净利润")
    eps: Optional[float] = Field(None, description="每股收益")


class BalanceSheetResponse(BaseModel):
    """资产负债表响应模型"""
    stock_code: str = Field(..., description="股票代码")
    report_date: date = Field(..., description="报告期")
    report_type: Optional[str] = Field(None, description="报告类型")
    total_assets: Optional[float] = Field(None, description="总资产")
    total_liability: Optional[float] = Field(None, description="总负债")
    total_equity: Optional[float] = Field(None, description="股东权益合计")
    current_assets: Optional[float] = Field(None, description="流动资产")
    current_liability: Optional[float] = Field(None, description="流动负债")


class CashFlowResponse(BaseModel):
    """现金流量表响应模型"""
    stock_code: str = Field(..., description="股票代码")
    report_date: date = Field(..., description="报告期")
    report_type: Optional[str] = Field(None, description="报告类型")
    operating_cash_flow: Optional[float] = Field(None, description="经营活动现金流")
    investing_cash_flow: Optional[float] = Field(None, description="投资活动现金流")
    financing_cash_flow: Optional[float] = Field(None, description="筹资活动现金流")
    cash_increase: Optional[float] = Field(None, description="现金净增加额")


class HolderInfoResponse(BaseModel):
    """股东信息响应模型"""
    stock_code: str = Field(..., description="股票代码")
    announce_date: Optional[date] = Field(None, description="公告日期")
    holder_name: Optional[str] = Field(None, description="股东名称")
    hold_amount: Optional[float] = Field(None, description="持股数量")
    hold_ratio: Optional[float] = Field(None, description="持股比例")
    holder_type: Optional[str] = Field(None, description="股东类型")


class DividendResponse(BaseModel):
    """分红送股响应模型"""
    stock_code: str = Field(..., description="股票代码")
    announce_date: Optional[date] = Field(None, description="公告日期")
    ex_dividend_date: Optional[date] = Field(None, description="除权除息日")
    cash_dividend: Optional[float] = Field(None, description="现金分红（元/10股）")
    stock_dividend: Optional[float] = Field(None, description="送股（股/10股）")
    transfer_dividend: Optional[float] = Field(None, description="转增股（股/10股）")
    progress: Optional[str] = Field(None, description="实施进度")


# 监控数据模型
class MonitorStatusResponse(BaseModel):
    """监控状态响应模型"""
    monitor_name: str = Field(..., description="监控名称")
    enabled: bool = Field(..., description="是否启用")
    interval: int = Field(..., description="监控间隔（秒）")
    failure_count: int = Field(..., description="连续失败次数")
    last_run_time: Optional[datetime] = Field(None, description="上次运行时间")
    last_alert_time: Optional[datetime] = Field(None, description="上次告警时间")


class AlertRecordResponse(BaseModel):
    """告警记录响应模型"""
    monitor_name: str = Field(..., description="监控名称")
    success: bool = Field(..., description="是否正常")
    message: str = Field(..., description="告警消息")
    level: str = Field(..., description="告警级别")
    metrics: Optional[dict] = Field(None, description="监控指标")
    details: Optional[dict] = Field(None, description="详细信息")
    timestamp: datetime = Field(..., description="告警时间")


class DashboardResponse(BaseModel):
    """监控面板响应模型"""
    monitor_count: int = Field(..., description="监控任务总数")
    running: bool = Field(..., description="调度器是否运行")
    monitor_status: List[MonitorStatusResponse] = Field(..., description="监控状态列表")
    recent_alerts: List[AlertRecordResponse] = Field(..., description="最近告警列表")
    alert_count_24h: int = Field(..., description="24小时告警总数")
    error_count: int = Field(..., description="错误级别告警数")
    warning_count: int = Field(..., description="警告级别告警数")


# 系统数据模型
class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    system_info: dict = Field(..., description="系统信息")
    cpu_info: dict = Field(..., description="CPU信息")
    memory_info: dict = Field(..., description="内存信息")
    disk_info: dict = Field(..., description="磁盘信息")
    storage_status: dict = Field(..., description="存储状态")
    data_source_status: dict = Field(..., description="数据源状态")
    timestamp: datetime = Field(..., description="查询时间")
