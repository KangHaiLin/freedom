"""
数据聚合处理器
负责按时间周期聚合、按股票聚合、滚动窗口计算、收益率计算、市场统计摘要
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from common.utils import NumberUtils

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class AggregationProcessor(BaseProcessor):
    """数据聚合处理器"""

    def __init__(self, config: Dict = None):
        super().__init__(config=config)

    def process(self, data: Any, **kwargs) -> Any:
        """
        统一处理入口
        Args:
            data: 输入DataFrame
            **kwargs:
                - agg_type: 聚合类型，支持:
                  'by_time', 'by_stock', 'rolling', 'expanding',
                  'returns', 'market_summary'
        Returns:
            聚合后的数据
        """
        if not self.validate_input(data):
            logger.warning(f"{self.name}: 输入数据验证失败")
            return data

        if not isinstance(data, pd.DataFrame):
            logger.warning(f"{self.name}: 输入必须是DataFrame")
            return data

        agg_type = kwargs.pop("agg_type", "by_time")

        if agg_type == "by_time":
            return self.aggregate_by_time(data, **kwargs)
        elif agg_type == "by_stock":
            return self.aggregate_by_stock(data, **kwargs)
        elif agg_type == "rolling":
            return self.rolling_aggregate(data, **kwargs)
        elif agg_type == "expanding":
            return self.expanding_aggregate(data, **kwargs)
        elif agg_type == "returns":
            return self.calculate_returns(data, **kwargs)
        elif agg_type == "market_summary":
            return self.market_summary(data, **kwargs)
        else:
            logger.warning(f"{self.name}: 未知的聚合类型: {agg_type}")
            return data

    def aggregate_by_time(
        self,
        df: pd.DataFrame,
        freq: str = "D",
        time_col: str = "trade_date",
        code_col: str = "ts_code",
        agg_map: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """
        按时间周期聚合
        Args:
            df: 输入DataFrame
            freq: 时间频率，'W'周，'M'月，'Q'季，'Y'年
            time_col: 时间列名
            code_col: 股票代码列名
            agg_map: 聚合映射，默认为None使用OHLC默认规则
        Returns:
            聚合后的DataFrame
        """
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col])

        # 默认聚合规则
        if agg_map is None:
            agg_map = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "amount": "sum"}

        # 如果有股票代码列，按股票和时间分组聚合
        if code_col in df.columns:
            grouped = df.groupby([code_col, pd.Grouper(key=time_col, freq=freq)])
            result = grouped.agg(agg_map).reset_index()
        else:
            grouped = df.groupby(pd.Grouper(key=time_col, freq=freq))
            result = grouped.agg(agg_map).reset_index()

        # 价格保留两位小数
        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            if col in result.columns:
                result[col] = result[col].apply(NumberUtils.round_price)

        return result

    def aggregate_by_stock(
        self, df: pd.DataFrame, code_col: str = "ts_code", agg_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        按股票聚合
        Args:
            df: 输入DataFrame
            code_col: 股票代码列名
            agg_map: 聚合映射
        Returns:
            聚合后的DataFrame
        """
        if agg_map is None:
            agg_map = {"close": ["mean", "min", "max"], "volume": ["sum", "mean"], "amount": "sum"}

        result = df.groupby(code_col).agg(agg_map).reset_index()
        # 扁平化多级索引
        result.columns = ["_".join(col).strip() if col[1] else col[0] for col in result.columns.values]
        return result

    def rolling_aggregate(
        self, df: pd.DataFrame, window: int, col: str, agg_func: str = "mean", min_periods: Optional[int] = None
    ) -> pd.Series:
        """
        滚动窗口聚合计算
        Args:
            df: 输入DataFrame
            window: 窗口大小
            col: 需要计算的列名
            agg_func: 聚合函数，'mean', 'sum', 'std', 'min', 'max'
            min_periods: 最小周期数，默认为window
        Returns:
            计算结果Series
        """
        min_periods = min_periods or window
        rolling = df[col].rolling(window=window, min_periods=min_periods)

        if agg_func == "mean":
            return rolling.mean()
        elif agg_func == "sum":
            return rolling.sum()
        elif agg_func == "std":
            return rolling.std()
        elif agg_func == "min":
            return rolling.min()
        elif agg_func == "max":
            return rolling.max()
        elif callable(agg_func):
            return rolling.apply(agg_func)
        else:
            logger.warning(f"{self.name}: 未知的聚合函数: {agg_func}")
            return df[col]

    def expanding_aggregate(
        self, df: pd.DataFrame, col: str, agg_func: str = "mean", min_periods: int = 1
    ) -> pd.Series:
        """
        扩张窗口聚合计算（从开始到当前累计）
        Args:
            df: 输入DataFrame
            col: 需要计算的列名
            agg_func: 聚合函数
            min_periods: 最小周期数
        Returns:
            计算结果Series
        """
        expanding = df[col].expanding(min_periods=min_periods)

        if agg_func == "mean":
            return expanding.mean()
        elif agg_func == "sum":
            return expanding.sum()
        elif agg_func == "std":
            return expanding.std()
        elif agg_func == "min":
            return expanding.min()
        elif agg_func == "max":
            return expanding.max()
        else:
            logger.warning(f"{self.name}: 未知的聚合函数: {agg_func}")
            return df[col]

    def calculate_returns(
        self, df: pd.DataFrame, price_col: str = "close", periods: int = 1, log_return: bool = False
    ) -> pd.DataFrame:
        """
        计算收益率
        Args:
            df: 输入DataFrame，需按时间排序
            price_col: 价格列名
            periods: 计算间隔期数
            log_return: 是否计算对数收益率
        Returns:
            添加了收益率列的DataFrame
        """
        df = df.copy()

        if log_return:
            df[f"return_{periods}"] = np.log(df[price_col] / df[price_col].shift(periods))
        else:
            df[f"return_{periods}"] = (df[price_col] - df[price_col].shift(periods)) / df[price_col].shift(periods)

        # 保留四位小数
        df[f"return_{periods}"] = df[f"return_{periods}"].round(4)

        return df

    def calculate_cumulative_returns(self, df: pd.DataFrame, return_col: str = "return_1") -> pd.Series:
        """
        计算累计收益率
        Args:
            df: 输入DataFrame，需按时间排序
            return_col: 收益率列名
        Returns:
            累计收益率Series
        """
        return (1 + df[return_col]).cumprod() - 1

    def market_summary(
        self, df: pd.DataFrame, date_col: str = "trade_date", code_col: str = "ts_code", return_col: str = "return_1"
    ) -> Dict:
        """
        计算市场整体统计摘要
        Args:
            df: 输入DataFrame
            date_col: 日期列名
            code_col: 股票代码列名
            return_col: 收益率列名
        Returns:
            统计摘要字典
        """
        summary = {}

        # 基本统计
        summary["total_dates"] = df[date_col].nunique()
        summary["total_stocks"] = df[code_col].nunique()
        summary["total_records"] = len(df)

        # 收益率统计
        if return_col in df.columns:
            daily_returns = df.groupby(date_col)[return_col].mean()
            summary["avg_daily_return"] = daily_returns.mean().round(4)
            summary["std_daily_return"] = daily_returns.std().round(4)
            summary["positive_days"] = (daily_returns > 0).sum()
            summary["negative_days"] = (daily_returns < 0).sum()
            summary["up_ratio"] = (summary["positive_days"] / len(daily_returns)).round(4)

        # 涨跌幅分布
        if return_col in df.columns:
            all_returns = df[return_col].dropna()
            summary["p10_return"] = np.percentile(all_returns, 10).round(4)
            summary["p50_return"] = np.percentile(all_returns, 50).round(4)
            summary["p90_return"] = np.percentile(all_returns, 90).round(4)
            summary["max_gain"] = all_returns.max().round(4)
            summary["max_loss"] = all_returns.min().round(4)

        return summary
