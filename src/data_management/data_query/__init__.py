"""
数据查询模块
提供统一的数据查询接口，支持跨存储引擎查询、分页、聚合、关联查询等高级功能
"""
from .base_query import BaseQuery
from .market_data_query import MarketDataQuery
from .fundamental_data_query import FundamentalDataQuery
from .query_manager import QueryManager, query_manager

__all__ = [
    'BaseQuery',
    'MarketDataQuery',
    'FundamentalDataQuery',
    'QueryManager',
    'query_manager'
]
