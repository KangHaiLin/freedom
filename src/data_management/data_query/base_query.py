"""
查询抽象基类
所有查询服务都需要实现此接口，提供统一的查询操作规范
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from common.exceptions import QueryException
from common.utils import DateTimeUtils, StockCodeUtils

logger = logging.getLogger(__name__)


class QueryCondition:
    """查询条件封装"""

    def __init__(self):
        self.stock_codes: Optional[List[str]] = None
        self.start_date: Optional[Union[str, date, datetime]] = None
        self.end_date: Optional[Union[str, date, datetime]] = None
        self.fields: Optional[List[str]] = None
        self.filters: Optional[Dict[str, Any]] = None
        self.order_by: Optional[Union[str, List[str]]] = None
        self.limit: Optional[int] = None
        self.offset: Optional[int] = None
        self.aggregation: Optional[Dict[str, Any]] = None
        self.group_by: Optional[List[str]] = None

    def validate(self) -> bool:
        """验证查询条件合法性"""
        if self.start_date and self.end_date:
            start = DateTimeUtils.parse(self.start_date)
            end = DateTimeUtils.parse(self.end_date)
            if start > end:
                raise QueryException("开始日期不能大于结束日期")

        if self.limit is not None and self.limit < 0:
            raise QueryException("limit不能为负数")

        if self.offset is not None and self.offset < 0:
            raise QueryException("offset不能为负数")

        return True

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "stock_codes": self.stock_codes,
            "start_date": DateTimeUtils.to_str(self.start_date) if self.start_date else None,
            "end_date": DateTimeUtils.to_str(self.end_date) if self.end_date else None,
            "fields": self.fields,
            "filters": self.filters,
            "order_by": self.order_by,
            "limit": self.limit,
            "offset": self.offset,
            "aggregation": self.aggregation,
            "group_by": self.group_by,
        }


class QueryResult:
    """查询结果封装"""

    def __init__(
        self,
        data: Union[pd.DataFrame, List[Dict]],
        total: int = 0,
        success: bool = True,
        message: str = "",
        query_time: float = 0.0,
    ):
        self.data = data
        self.total = total if total is not None else (len(data) if data is not None else 0)
        self.success = success
        self.message = message
        self.query_time = query_time
        self.timestamp = DateTimeUtils.now()

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        data_dict = []
        if isinstance(self.data, pd.DataFrame):
            data_dict = self.data.to_dict("records")
        elif isinstance(self.data, list):
            data_dict = self.data

        return {
            "data": data_dict,
            "total": self.total,
            "success": self.success,
            "message": self.message,
            "query_time": round(self.query_time, 3),
            "timestamp": DateTimeUtils.to_str(self.timestamp),
        }

    def to_df(self) -> pd.DataFrame:
        """转换为DataFrame格式"""
        if isinstance(self.data, pd.DataFrame):
            return self.data
        elif isinstance(self.data, list):
            return pd.DataFrame(self.data)
        else:
            return pd.DataFrame()


class BaseQuery(ABC):
    """查询抽象基类"""

    def __init__(self, storage_manager):
        self.storage_manager = storage_manager
        self.default_page_size = 1000
        self.max_page_size = 10000

    @abstractmethod
    def query(self, condition: QueryCondition) -> QueryResult:
        """
        执行查询
        Args:
            condition: 查询条件
        Returns:
            查询结果
        """
        pass

    def _validate_condition(self, condition: QueryCondition) -> None:
        """验证查询条件"""
        try:
            condition.validate()
        except Exception as e:
            logger.error(f"查询条件验证失败：{e}")
            raise QueryException(f"查询条件验证失败：{e}") from e

    def _normalize_stock_codes(self, stock_codes: List[str]) -> List[str]:
        """标准化股票代码"""
        if not stock_codes:
            return []
        return [StockCodeUtils.normalize_code(code) for code in stock_codes]

    def _normalize_dates(
        self, start_date: Optional[Union[str, date, datetime]], end_date: Optional[Union[str, date, datetime]]
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """标准化日期时间"""
        normalized_start = DateTimeUtils.parse(start_date) if start_date else None
        normalized_end = DateTimeUtils.parse(end_date) if end_date else None

        # 如果没有结束日期，默认到当前时间
        if normalized_start and not normalized_end:
            normalized_end = DateTimeUtils.now()

        # 如果只有结束日期，默认开始日期为30天前
        if normalized_end and not normalized_start:
            normalized_start = normalized_end - timedelta(days=30)

        return normalized_start, normalized_end

    def _apply_pagination(self, df: pd.DataFrame, limit: Optional[int], offset: Optional[int]) -> pd.DataFrame:
        """应用分页"""
        if offset is not None:
            df = df.iloc[offset:]
        if limit is not None:
            df = df.iloc[:limit]
        return df

    def _apply_order_by(self, df: pd.DataFrame, order_by: Optional[Union[str, List[str]]]) -> pd.DataFrame:
        """应用排序"""
        if not order_by or df.empty:
            return df

        if isinstance(order_by, str):
            order_by = [order_by]

        sort_columns = []
        ascending = []
        for col in order_by:
            if col.startswith("-"):
                col_name = col[1:]
                if col_name in df.columns:
                    sort_columns.append(col_name)
                    ascending.append(False)
            else:
                if col in df.columns:
                    sort_columns.append(col)
                    ascending.append(True)

        # 只对存在的列进行排序
        if sort_columns:
            df = df.sort_values(by=sort_columns, ascending=ascending)

        return df

    def _apply_filters(self, df: pd.DataFrame, filters: Optional[Dict[str, Any]]) -> pd.DataFrame:
        """应用过滤条件"""
        if not filters or df.empty:
            return df

        for key, value in filters.items():
            if key not in df.columns:
                continue

            if isinstance(value, list):
                df = df[df[key].isin(value)]
            elif isinstance(value, str) and ("%" in value or "_" in value):
                # 模糊匹配
                pattern = value.replace("%", ".*").replace("_", ".")
                df = df[df[key].astype(str).str.match(pattern)]
            else:
                df = df[df[key] == value]

        return df
