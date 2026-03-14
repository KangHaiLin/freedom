"""
行情数据查询服务
提供行情数据的统一查询接口，支持实时行情、日线、分钟线、Tick数据查询
"""
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from datetime import datetime, date, timedelta
import time

from .base_query import BaseQuery, QueryCondition, QueryResult
from common.exceptions import QueryException
from common.utils import DateTimeUtils, StockCodeUtils
import logging

logger = logging.getLogger(__name__)


class MarketDataQuery(BaseQuery):
    """行情数据查询服务"""

    def __init__(self, storage_manager):
        super().__init__(storage_manager)
        self.clickhouse_storage = storage_manager.get_storage_by_type('clickhouse')
        self.postgresql_storage = storage_manager.get_storage_by_type('postgresql')
        self.redis_storage = storage_manager.get_storage_by_type('redis')

        # 表名配置
        self.table_config = {
            'realtime': 'market_realtime_quote',
            'daily': 'market_daily_quote',
            'minute': 'market_minute_quote',
            'tick': 'market_tick_quote'
        }

    def query(self, condition: QueryCondition) -> QueryResult:
        """执行行情数据查询"""
        start_time = time.time()
        try:
            self._validate_condition(condition)

            # 确定数据类型
            data_type = condition.filters.get('data_type', 'daily') if condition.filters else 'daily'
            if data_type not in self.table_config:
                raise QueryException(f"不支持的行情数据类型：{data_type}")

            # 先尝试从缓存查询
            cache_key = self._build_cache_key(condition)
            if self.redis_storage:
                cache_result = self.redis_storage.read('query_cache', {'key': cache_key})
                if cache_result:
                    logger.debug(f"缓存命中：{cache_key}")
                    return QueryResult(
                        data=pd.DataFrame(cache_result),
                        query_time=time.time() - start_time,
                        success=True,
                        message="缓存命中"
                    )

            # 根据数据类型选择合适的存储
            storage = self.clickhouse_storage if data_type in ['daily', 'minute', 'tick'] else self.postgresql_storage
            if not storage:
                raise QueryException(f"无可用存储引擎查询{data_type}数据")

            table_name = self.table_config[data_type]
            query_dict = self._build_query_dict(condition, data_type)

            # 执行查询
            df = storage.read(
                table_name=table_name,
                query=query_dict,
                order_by=condition.order_by,
                limit=condition.limit,
                offset=condition.offset
            )

            # 应用后置过滤和处理
            df = self._apply_filters(df, condition.filters)
            df = self._apply_order_by(df, condition.order_by)
            df = self._select_fields(df, condition.fields)

            # 缓存结果
            if self.redis_storage and not df.empty and len(df) < 10000:
                self.redis_storage.write(
                    'query_cache',
                    df,
                    key=cache_key,
                    ttl=300  # 缓存5分钟
                )

            query_time = time.time() - start_time
            logger.debug(f"行情查询成功，数据类型：{data_type}，记录数：{len(df)}，耗时：{query_time:.3f}s")

            return QueryResult(
                data=df,
                total=len(df),
                query_time=query_time,
                success=True
            )

        except Exception as e:
            logger.error(f"行情查询失败：{e}")
            return QueryResult(
                data=[],
                success=False,
                message=str(e),
                query_time=time.time() - start_time
            )

    def _build_cache_key(self, condition: QueryCondition) -> str:
        """构建缓存键"""
        cond_dict = condition.to_dict()
        key_parts = ["market_query"]
        for key, value in sorted(cond_dict.items()):
            if value is not None:
                key_parts.append(f"{key}:{str(value)}")
        return ":".join(key_parts)

    def _build_query_dict(self, condition: QueryCondition, data_type: str) -> Dict:
        """构建查询条件字典"""
        query_dict = {}

        # 股票代码过滤
        if condition.stock_codes:
            normalized_codes = self._normalize_stock_codes(condition.stock_codes)
            query_dict['stock_code'] = normalized_codes

        # 时间范围过滤
        start_date, end_date = self._normalize_dates(condition.start_date, condition.end_date)
        if start_date and end_date:
            time_column = self._get_time_column(data_type)
            query_dict[time_column] = (start_date, end_date)

        # 其他过滤条件
        if condition.filters:
            for key, value in condition.filters.items():
                if key not in ['data_type']:
                    query_dict[key] = value

        return query_dict

    def _get_time_column(self, data_type: str) -> str:
        """根据数据类型获取时间列名"""
        time_columns = {
            'realtime': 'time',
            'daily': 'trade_date',
            'minute': 'trade_time',
            'tick': 'trade_time'
        }
        return time_columns.get(data_type, 'time')

    def _select_fields(self, df: pd.DataFrame, fields: Optional[List[str]]) -> pd.DataFrame:
        """选择需要的字段"""
        if not fields or df.empty:
            return df

        valid_fields = [field for field in fields if field in df.columns]
        if valid_fields:
            return df[valid_fields].copy()
        return df

    # 快捷查询方法
    def get_realtime_quote(
        self,
        stock_codes: List[str],
        fields: Optional[List[str]] = None
    ) -> QueryResult:
        """获取实时行情"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.fields = fields
        condition.filters = {'data_type': 'realtime'}
        condition.order_by = ['stock_code']
        return self.query(condition)

    def get_daily_quote(
        self,
        stock_codes: List[str],
        start_date: Union[str, date, datetime],
        end_date: Optional[Union[str, date, datetime]] = None,
        fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> QueryResult:
        """获取日线行情"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {'data_type': 'daily'}
        condition.order_by = order_by or ['trade_date', 'stock_code']
        return self.query(condition)

    def get_minute_quote(
        self,
        stock_codes: List[str],
        start_date: Union[str, date, datetime],
        end_date: Optional[Union[str, date, datetime]] = None,
        period: int = 1,
        fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> QueryResult:
        """获取分钟线行情"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {
            'data_type': 'minute',
            'period': period
        }
        condition.order_by = order_by or ['trade_time', 'stock_code']
        return self.query(condition)

    def get_tick_quote(
        self,
        stock_codes: List[str],
        date: Union[str, date, datetime],
        fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> QueryResult:
        """获取Tick行情"""
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = date
        condition.end_date = date
        condition.fields = fields
        condition.filters = {'data_type': 'tick'}
        condition.order_by = order_by or ['trade_time']
        return self.query(condition)

    def get_latest_daily_quote(
        self,
        stock_codes: List[str],
        days: int = 1,
        fields: Optional[List[str]] = None
    ) -> QueryResult:
        """获取最近N天的日线行情"""
        end_date = DateTimeUtils.now()
        start_date = end_date - timedelta(days=days * 2)  # 多取2天避免节假日
        condition = QueryCondition()
        condition.stock_codes = stock_codes
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = fields
        condition.filters = {'data_type': 'daily'}
        condition.order_by = ['-trade_date', 'stock_code']
        condition.limit = len(stock_codes) * days

        result = self.query(condition)
        if not result.data.empty:
            # 只保留最近days天的数据
            df = result.to_df()
            latest_dates = df['trade_date'].sort_values(ascending=False).unique()[:days]
            result.data = df[df['trade_date'].isin(latest_dates)].sort_values(['trade_date', 'stock_code'])
            result.total = len(result.data)

        return result

    def calculate_ma(
        self,
        stock_code: str,
        periods: List[int],
        days: int = 250
    ) -> QueryResult:
        """计算均线"""
        end_date = DateTimeUtils.now()
        start_date = end_date - timedelta(days=days + max(periods))

        condition = QueryCondition()
        condition.stock_codes = [stock_code]
        condition.start_date = start_date
        condition.end_date = end_date
        condition.fields = ['trade_date', 'close']
        condition.filters = {'data_type': 'daily'}
        condition.order_by = ['trade_date']

        result = self.query(condition)
        if result.data.empty:
            return result

        df = result.to_df()
        for period in periods:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean().round(2)

        # 只保留最近days天的数据
        df = df.tail(days).reset_index(drop=True)
        result.data = df
        result.total = len(df)

        return result
