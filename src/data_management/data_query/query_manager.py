"""
查询管理器
统一管理所有查询服务，提供统一的查询入口，支持查询路由、缓存、权限控制等
"""
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from datetime import datetime, date
import time
import logging

from .base_query import QueryCondition, QueryResult
from .market_data_query import MarketDataQuery
from .fundamental_data_query import FundamentalDataQuery
from ..data_storage.storage_manager import storage_manager
from common.config import settings
from common.exceptions import QueryException
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class QueryManager:
    """查询管理器，提供统一查询入口"""

    def __init__(self):
        self.storage_manager = storage_manager
        self.query_services = {}
        self._init_query_services()

        # 配置项
        self.enable_cache = settings.QUERY_CONFIG.get('enable_cache', True)
        self.max_query_limit = settings.QUERY_CONFIG.get('max_query_limit', 100000)
        default_timeout = settings.QUERY_CONFIG.get('query_timeout', 30)
        self.query_timeout = max(5, default_timeout)  # 最少5秒超时

    def _init_query_services(self):
        """初始化查询服务"""
        try:
            self.query_services['market'] = MarketDataQuery(self.storage_manager)
            self.query_services['fundamental'] = FundamentalDataQuery(self.storage_manager)
            logger.info("所有查询服务初始化完成")
        except Exception as e:
            logger.error(f"初始化查询服务失败：{e}")
            raise QueryException(f"初始化查询服务失败：{e}") from e

    def get_query_service(self, service_type: str):
        """获取查询服务实例"""
        service = self.query_services.get(service_type.lower())
        if not service:
            raise QueryException(f"不支持的查询服务类型：{service_type}")
        return service

    def query(
        self,
        service_type: str,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Union[str, List[str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs
    ) -> QueryResult:
        """
        统一查询入口
        Args:
            service_type: 服务类型：market/fundamental
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 需要返回的字段列表
            filters: 过滤条件字典
            order_by: 排序字段，支持-开头表示降序
            limit: 返回记录数限制
            offset: 偏移量
            **kwargs: 其他参数
        Returns:
            查询结果
        """
        start_time = time.time()
        try:
            # 构建查询条件
            condition = QueryCondition()
            condition.stock_codes = stock_codes
            condition.start_date = start_date
            condition.end_date = end_date
            condition.fields = fields
            condition.filters = filters or {}
            condition.order_by = order_by
            condition.limit = min(limit, self.max_query_limit) if limit else self.max_query_limit
            condition.offset = offset

            # 合并额外参数到filters
            condition.filters.update(kwargs)

            # 验证查询条件
            condition.validate()

            # 获取查询服务
            service = self.get_query_service(service_type)

            # 执行查询
            result = service.query(condition)
            result.query_time = time.time() - start_time

            # 记录慢查询
            if result.query_time > 5:
                logger.warning(f"慢查询：服务={service_type}，条件={condition.to_dict()}，耗时={result.query_time:.3f}s")

            return result

        except Exception as e:
            logger.error(f"查询失败：{e}")
            return QueryResult(
                data=[],
                success=False,
                message=str(e),
                query_time=time.time() - start_time
            )

    # 快捷行情查询方法
    def get_realtime_quote(
        self,
        stock_codes: List[str],
        fields: Optional[List[str]] = None
    ) -> QueryResult:
        """获取实时行情"""
        return self.get_query_service('market').get_realtime_quote(stock_codes, fields)

    def get_daily_quote(
        self,
        stock_codes: List[str],
        start_date: Union[str, date, datetime],
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取日线行情"""
        return self.get_query_service('market').get_daily_quote(
            stock_codes, start_date, end_date, fields, **kwargs
        )

    def get_minute_quote(
        self,
        stock_codes: List[str],
        start_date: Union[str, date, datetime],
        end_date: Optional[Union[str, date, datetime]] = None,
        period: int = 1,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取分钟线行情"""
        return self.get_query_service('market').get_minute_quote(
            stock_codes, start_date, end_date, period, fields, **kwargs
        )

    def get_tick_quote(
        self,
        stock_codes: List[str],
        date: Union[str, date, datetime],
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取Tick行情"""
        return self.get_query_service('market').get_tick_quote(
            stock_codes, date, fields, **kwargs
        )

    # 快捷基本面查询方法
    def get_stock_basic(
        self,
        stock_codes: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取股票基础信息"""
        return self.get_query_service('fundamental').get_stock_basic(
            stock_codes, fields, **kwargs
        )

    def get_financial_indicator(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取财务指标"""
        return self.get_query_service('fundamental').get_financial_indicator(
            stock_codes, start_date, end_date, fields, **kwargs
        )

    def get_income_statement(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取利润表"""
        return self.get_query_service('fundamental').get_income_statement(
            stock_codes, start_date, end_date, fields, **kwargs
        )

    def get_balance_sheet(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取资产负债表"""
        return self.get_query_service('fundamental').get_balance_sheet(
            stock_codes, start_date, end_date, fields, **kwargs
        )

    def get_cash_flow(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        **kwargs
    ) -> QueryResult:
        """获取现金流量表"""
        return self.get_query_service('fundamental').get_cash_flow(
            stock_codes, start_date, end_date, fields, **kwargs
        )

    def batch_query(
        self,
        queries: List[Dict]
    ) -> List[QueryResult]:
        """
        批量查询
        Args:
            queries: 查询列表，每个查询为字典格式，包含查询参数
        Returns:
            查询结果列表
        """
        results = []
        for query_params in queries:
            try:
                result = self.query(**query_params)
                results.append(result)
            except Exception as e:
                results.append(QueryResult(
                    data=[],
                    success=False,
                    message=str(e)
                ))
        return results

    def health_check(self) -> Dict:
        """查询服务健康检查"""
        health_status = {
            "status": "healthy",
            "query_services": {},
            "storage_health": self.storage_manager.health_check(),
            "check_time": DateTimeUtils.now_str()
        }

        for name, service in self.query_services.items():
            try:
                # 简单测试查询
                test_condition = QueryCondition()
                test_condition.limit = 1
                result = service.query(test_condition)
                health_status["query_services"][name] = {
                    "status": "healthy" if result.success else "unhealthy",
                    "message": result.message
                }
            except Exception as e:
                health_status["query_services"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "unhealthy"

        return health_status

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """清除查询缓存"""
        redis_storage = self.storage_manager.get_storage_by_type('redis')
        if not redis_storage:
            return 0

        try:
            if pattern:
                deleted = redis_storage.delete('query_cache', {'pattern': pattern})
            else:
                deleted = redis_storage.delete('query_cache', {'pattern': 'query_cache:*'})
                deleted += redis_storage.delete('fundamental_query_cache', {'pattern': 'fundamental_query_cache:*'})
            logger.info(f"清除缓存成功，删除键数：{deleted}")
            return deleted
        except Exception as e:
            logger.error(f"清除缓存失败：{e}")
            return 0


# 全局查询管理器实例
query_manager = QueryManager()
