"""
数据转换处理器
负责数据格式转换、数据类型转换、列重命名、日期时间标准化、时间序列重采样
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from common.utils import DateTimeUtils, NumberUtils, StockCodeUtils

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class TransformationProcessor(BaseProcessor):
    """数据转换处理器"""

    def __init__(self, config: Dict = None):
        super().__init__(config=config)
        self.default_date_format = self.config.get("default_date_format", "%Y-%m-%d")
        self.default_datetime_format = self.config.get("default_datetime_format", "%Y-%m-%d %H:%M:%S")

    def process(self, data: Any, **kwargs) -> Any:
        """
        统一处理入口，根据kwargs选择具体转换方法
        Args:
            data: 输入数据
            **kwargs:
                - transform_type: 转换类型，支持:
                  'list_to_df', 'df_to_list', 'dtype', 'rename_columns',
                  'normalize_datetime', 'resample', 'stock_code_normalize'
        Returns:
            转换后的数据
        """
        if not self.validate_input(data):
            logger.warning(f"{self.name}: 输入数据验证失败")
            return data

        transform_type = kwargs.pop("transform_type", "list_to_df")

        if transform_type == "list_to_df":
            return self.list_to_dataframe(data, **kwargs)
        elif transform_type == "df_to_list":
            return self.dataframe_to_list(data, **kwargs)
        elif transform_type == "dtype":
            return self.convert_dtypes(data, **kwargs)
        elif transform_type == "rename_columns":
            return self.rename_columns(data, **kwargs)
        elif transform_type == "normalize_datetime":
            return self.normalize_datetime(data, **kwargs)
        elif transform_type == "resample":
            return self.resample(data, **kwargs)
        elif transform_type == "stock_code_normalize":
            return self.normalize_stock_code(data, **kwargs)
        else:
            logger.warning(f"{self.name}: 未知的转换类型: {transform_type}")
            return data

    def list_to_dataframe(self, data: List[Dict], index_col: Optional[str] = None) -> pd.DataFrame:
        """
        将列表字典转换为DataFrame
        Args:
            data: 列表字典数据
            index_col: 索引列名
        Returns:
            DataFrame
        """
        df = pd.DataFrame(data)
        if index_col and index_col in df.columns:
            df = df.set_index(index_col)
        return df

    def dataframe_to_list(self, df: pd.DataFrame, orient: str = "records") -> List[Dict]:
        """
        将DataFrame转换为列表字典
        Args:
            df: DataFrame
            orient: 输出方向，默认'records'
        Returns:
            列表字典
        """
        return df.to_dict(orient)

    def convert_dtypes(self, df: pd.DataFrame, dtype_map: Dict[str, str]) -> pd.DataFrame:
        """
        转换数据列类型
        Args:
            df: 输入DataFrame
            dtype_map: 类型映射，{列名: 目标类型}
        Returns:
            转换后的DataFrame
        """
        df = df.copy()
        for col, dtype in dtype_map.items():
            if col in df.columns:
                try:
                    if dtype == "datetime" or dtype == "datetime64":
                        df[col] = pd.to_datetime(df[col])
                    elif dtype == "float":
                        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
                    elif dtype == "int":
                        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                    elif dtype == "string":
                        df[col] = df[col].astype(str)
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"{self.name}: 转换列{col}为{dtype}失败: {e}")
        return df

    def rename_columns(self, df: pd.DataFrame, rename_map: Dict[str, str]) -> pd.DataFrame:
        """
        重命名列
        Args:
            df: 输入DataFrame
            rename_map: 重命名映射，{原列名: 新列名}
        Returns:
            重命名后的DataFrame
        """
        return df.rename(columns=rename_map)

    def normalize_datetime(
        self, df: pd.DataFrame, datetime_cols: List[str] = None, date_cols: List[str] = None, output_format: str = None
    ) -> pd.DataFrame:
        """
        标准化日期时间格式
        Args:
            df: 输入DataFrame
            datetime_cols: 需要标准化为datetime的列名列表
            date_cols: 需要标准化为date的列名列表
            output_format: 输出格式，默认使用配置的default_datetime_format
        Returns:
            标准化后的DataFrame
        """
        df = df.copy()
        output_format = output_format or self.default_datetime_format

        if datetime_cols:
            for col in datetime_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    if output_format:
                        df[col] = df[col].dt.strftime(output_format)

        if date_cols:
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.date
                    if output_format:
                        df[col] = df[col].apply(lambda x: x.strftime(self.default_date_format))

        return df

    def normalize_stock_code(self, df: pd.DataFrame, code_col: str = "ts_code") -> pd.DataFrame:
        """
        标准化股票代码
        Args:
            df: 输入DataFrame
            code_col: 股票代码列名
        Returns:
            标准化后的DataFrame
        """
        df = df.copy()
        if code_col in df.columns:
            df[code_col] = df[code_col].apply(StockCodeUtils.normalize)
        return df

    def resample(
        self, df: pd.DataFrame, rule: str, datetime_col: str = "trade_time", agg_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        时间序列重采样（例如Tick数据转分钟线）
        Args:
            df: 输入DataFrame
            rule: 重采样规则，例如 '1T', '5T', '15T', '30T', '60T', 'D'
            datetime_col: 时间列名
            agg_map: 聚合映射，{列名: 聚合方法}，如果不提供则使用默认聚合
        Returns:
            重采样后的DataFrame
        """
        df = df.copy()

        # 将时间列设为索引
        if datetime_col in df.columns:
            df = df.set_index(pd.to_datetime(df[datetime_col]))

        # 默认聚合规则
        if agg_map is None:
            # 对于OHLC数据使用标准聚合
            default_agg = {}
            if "open" in df.columns:
                default_agg["open"] = "first"
            if "high" in df.columns:
                default_agg["high"] = "max"
            if "low" in df.columns:
                default_agg["low"] = "min"
            if "close" in df.columns:
                default_agg["close"] = "last"
            if "volume" in df.columns:
                default_agg["volume"] = "sum"
            if "amount" in df.columns:
                default_agg["amount"] = "sum"
            agg_map = default_agg

        # 执行重采样聚合
        resampled = df.resample(rule).agg(agg_map)

        # 重置索引，恢复时间列
        resampled = resampled.reset_index()

        # 价格保留两位小数（A股标准）
        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            if col in resampled.columns:
                resampled[col] = resampled[col].apply(NumberUtils.round_price)

        return resampled
