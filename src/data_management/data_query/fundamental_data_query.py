"""
基本面数据查询服务
提供股票基本面数据的统一查询接口，支持财务报表、财务指标、股东信息等查询
"""

import logging
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from common.exceptions import QueryException

from .base_query import BaseQuery, QueryCondition, QueryResult

logger = logging.getLogger(__name__)


class FundamentalDataQuery(BaseQuery):
    """基本面数据查询服务"""

    def __init__(self, storage_manager):
        super().__init__(storage_manager)
        self.postgresql_storage = storage_manager.get_storage_by_type("postgresql")
        self.clickhouse_storage = storage_manager.get_storage_by_type("clickhouse")
        self.redis_storage = storage_manager.get_storage_by_type("redis")

        # 表名配置
        self.table_config = {
            "income_statement": "fundamental_income_statement",
            "balance_sheet": "fundamental_balance_sheet",
            "cash_flow": "fundamental_cash_flow",
            "financial_indicator": "fundamental_financial_indicator",
            "stock_basic": "fundamental_stock_basic",
            "holder": "fundamental_holder",
            "dividend": "fundamental_dividend",
        }

    def query(self, condition: QueryCondition) -> QueryResult:
        """执行基本面数据查询"""
        start_time = time.time()
        try:
            self._validate_condition(condition)

            # 确定数据类型
            data_type = (
                condition.filters.get("data_type", "financial_indicator")
                if condition.filters
                else "financial_indicator"
            )
            if data_type not in self.table_config:
                raise QueryException(f"不支持的基本面数据类型：{data_type}")

            # 缓存查询
            cache_key = self._build_cache_key(condition)
            if self.redis_storage is not None:
                cache_result = self.redis_storage.read("fundamental_query_cache", {"key": cache_key})
                if cache_result is not None:
                    logger.debug(f"基本面缓存命中：{cache_key}")
                    if isinstance(cache_result, pd.DataFrame):
                        return QueryResult(
                            data=cache_result,
                            query_time=time.time() - start_time,
                            success=True,
                            message="缓存命中",
                        )
                    else:
                        return QueryResult(
                            data=pd.DataFrame(cache_result),
                            query_time=time.time() - start_time,
                            success=True,
                            message="缓存命中",
                        )

            # 选择存储引擎
            storage = (
                self.postgresql_storage
                if data_type in ["stock_basic", "holder", "dividend"]
                else self.clickhouse_storage
            )
            if storage is None:
                raise QueryException(f"无可用存储引擎查询{data_type}数据")

            table_name = self.table_config[data_type]
            query_dict = self._build_query_dict(condition)

            # 执行查询
            df = storage.read(
                table_name=table_name,
                query=query_dict,
                order_by=condition.order_by,
                limit=condition.limit,
                offset=condition.offset,
            )

            # 应用后置处理
            df = self._apply_filters(df, condition.filters)
            df = self._apply_order_by(df, condition.order_by)
            df = self._select_fields(df, condition.fields)

            # 缓存结果
            if self.redis_storage is not None and not df.empty and len(df) < 5000:
                self.redis_storage.write("fundamental_query_cache", df, key=cache_key, ttl=3600)  # 缓存1小时

            query_time = time.time() - start_time
            logger.debug(f"基本面查询成功，数据类型：{data_type}，记录数：{len(df)}，耗时：{query_time:.3f}s")

            return QueryResult(data=df, total=len(df), query_time=query_time, success=True)

        except Exception as e:
            logger.error(f"基本面查询失败：{e}")
            return QueryResult(data=[], success=False, message=str(e), query_time=time.time() - start_time)

    def _build_cache_key(self, condition: QueryCondition) -> str:
        """构建缓存键"""
        cond_dict = condition.to_dict()
        key_parts = ["fundamental_query"]
        for key, value in sorted(cond_dict.items()):
            if value is not None:
                key_parts.append(f"{key}:{str(value)}")
        return ":".join(key_parts)

    def _build_query_dict(self, condition: QueryCondition) -> Dict:
        """构建查询条件字典"""
        query_dict = {}

        # 股票代码过滤
        if condition.stock_codes:
            normalized_codes = self._normalize_stock_codes(condition.stock_codes)
            query_dict["stock_code"] = normalized_codes

        # 报告期过滤
        if condition.start_date or condition.end_date:
            start_date, end_date = self._normalize_dates(condition.start_date, condition.end_date)
            if start_date and end_date:
                query_dict["report_date"] = (start_date, end_date)

        # 其他过滤条件
        if condition.filters:
            for key, value in condition.filters.items():
                if key not in ["data_type"]:
                    query_dict[key] = value

        return query_dict

    def _select_fields(self, df: pd.DataFrame, fields: Optional[List[str]]) -> pd.DataFrame:
        """选择需要的字段"""
        if not fields or df.empty:
            return df

        valid_fields = [field for field in fields if field in df.columns]
        if valid_fields:
            return df[valid_fields].copy()
        return df

    # 快捷查询方法
    def get_stock_basic(
        self,
        stock_codes: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """获取股票基础信息"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.fields = fields
        condition.filters = {"data_type": "stock_basic"}
        if filters:
            condition.filters.update(filters)
        condition.order_by = ["stock_code"]
        return self.query(condition)

    def get_financial_indicator(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
    ) -> QueryResult:
        """获取财务指标"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {"data_type": "financial_indicator"}
        condition.order_by = order_by or ["-report_date", "stock_code"]
        return self.query(condition)

    def get_income_statement(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        report_type: Optional[str] = None,  # 报告类型：Q1/Q2/Q3/Q4/ALL
    ) -> QueryResult:
        """获取利润表"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {"data_type": "income_statement"}
        if report_type:
            condition.filters["report_type"] = report_type
        condition.order_by = ["-report_date", "stock_code"]
        return self.query(condition)

    def get_balance_sheet(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        report_type: Optional[str] = None,
    ) -> QueryResult:
        """获取资产负债表"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {"data_type": "balance_sheet"}
        if report_type:
            condition.filters["report_type"] = report_type
        condition.order_by = ["-report_date", "stock_code"]
        return self.query(condition)

    def get_cash_flow(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        report_type: Optional[str] = None,
    ) -> QueryResult:
        """获取现金流量表"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {"data_type": "cash_flow"}
        if report_type:
            condition.filters["report_type"] = report_type
        condition.order_by = ["-report_date", "stock_code"]
        return self.query(condition)

    def get_holder_info(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        holder_type: Optional[str] = None,  # 股东类型：top10/top10_flow/manager
    ) -> QueryResult:
        """获取股东信息"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.filters = {"data_type": "holder"}
        if holder_type:
            condition.filters["holder_type"] = holder_type
        condition.order_by = ["-announce_date", "stock_code"]
        return self.query(condition)

    def get_dividend(
        self,
        stock_codes: List[str],
        start_date: Optional[Union[str, date, datetime]] = None,
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
    ) -> QueryResult:
        """获取分红送股信息"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {"data_type": "dividend"}
        condition.order_by = ["-ex_dividend_date", "stock_code"]
        return self.query(condition)

    def get_latest_financial_report(self, stock_codes: List[str], report_count: int = 4) -> QueryResult:
        """获取最新财务报告"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.filters = {"data_type": "financial_indicator"}
        condition.order_by = ["-report_date", "stock_code"]
        condition.limit = len(stock_codes) * report_count

        result = self.query(condition)
        if not result.data.empty:
            # 每个股票只保留最新的report_count个报告
            df = result.to_df()
            result.data = df.groupby("stock_code").head(report_count).reset_index(drop=True)
            result.total = len(result.data)

        return result
