"""
数据合并处理器
负责按股票+日期合并行情和基本面、合并多个数据集、对齐时间范围、缺失值填充
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class MergingProcessor(BaseProcessor):
    """数据合并处理器"""

    def __init__(self, config: Dict = None):
        super().__init__(config=config)

    def process(self, data: Any, merge_type: str = "market_fundamental", **kwargs) -> Optional[pd.DataFrame]:
        """
        合并处理入口
        Args:
            data: 数据列表或元组
            merge_type: 合并类型，支持:
                'market_fundamental' - 行情+基本面按股票日期合并
                'concat' - 垂直拼接多个数据集
                'join' - 水平连接多个数据集
                'align_time' - 对齐多个数据集时间范围
        Returns:
            合并后的DataFrame
        """
        if data is None:
            logger.warning(f"{self.name}: 输入数据为空")
            return None

        if not isinstance(data, (list, tuple)):
            logger.warning(f"{self.name}: 输入必须是数据列表或元组")
            return None

        if len(data) < 2:
            logger.warning(f"{self.name}: 需要至少两个数据集才能合并")
            return data[0] if data else None

        # merge_type已经作为位置参数弹出了，不需要处理

        if merge_type == "market_fundamental":
            return self.merge_market_fundamental(data[0], data[1], **kwargs)
        elif merge_type == "concat":
            return self.concat_datasets(data, **kwargs)
        elif merge_type == "join":
            return self.join_datasets(data, **kwargs)
        elif merge_type == "align_time":
            return self.align_time_range(data, **kwargs)
        else:
            logger.warning(f"{self.name}: 未知的合并类型: {merge_type}")
            return None

    def merge_market_fundamental(
        self,
        market_data: pd.DataFrame,
        fundamental_data: pd.DataFrame,
        how: str = "left",
        code_col: str = "ts_code",
        date_col: str = "trade_date",
        ffill: bool = True,
    ) -> pd.DataFrame:
        """
        合并行情数据和基本面数据，按股票代码+日期合并
        Args:
            market_data: 行情数据，包含每日行情
            fundamental_data: 基本面数据，包含季报/年报数据
            how: 连接方式，'left', 'inner', 'outer'
            code_col: 股票代码列名
            date_col: 日期列名
            ffill: 是否对基本面数据进行前向填充
        Returns:
            合并后的DataFrame
        """
        # 检查输入
        if market_data.empty or fundamental_data.empty:
            logger.warning(f"{self.name}: 行情数据或基本面数据为空")
            return market_data

        # 确保日期列格式一致
        market_data = market_data.copy()
        fundamental_data = fundamental_data.copy()

        market_data[date_col] = pd.to_datetime(market_data[date_col])
        fundamental_data[date_col] = pd.to_datetime(fundamental_data[date_col])

        # 合并
        merged = pd.merge(
            market_data, fundamental_data, on=[code_col, date_col], how=how, suffixes=("_market", "_fund")
        )

        # 前向填充基本面数据（因为基本面不每天更新，需要填充）
        if ffill and how == "left":
            # 找出所有来自基本面的列（不是合并键，也不是market原有的）
            market_cols = set(market_data.columns)
            fund_cols = []
            for col in merged.columns:
                if col not in [code_col, date_col] and col not in market_cols:
                    fund_cols.append(col)
                elif col.endswith("_fund"):
                    fund_cols.append(col)
            if fund_cols:
                merged[fund_cols] = merged.groupby(code_col)[fund_cols].ffill()

        # 排序
        merged = merged.sort_values([code_col, date_col]).reset_index(drop=True)

        return merged

    def concat_datasets(
        self, datasets: List[pd.DataFrame], ignore_index: bool = True, verify_integrity: bool = False
    ) -> pd.DataFrame:
        """
        垂直拼接多个数据集（按行拼接），常用于合并多股票数据、多日期数据
        Args:
            datasets: DataFrame列表
            ignore_index: 是否忽略原有索引
            verify_integrity: 是否检查重复索引
        Returns:
            拼接后的DataFrame
        """
        # 过滤空数据集
        non_empty = [df for df in datasets if not df.empty]

        if not non_empty:
            logger.warning(f"{self.name}: 所有数据集都为空")
            return pd.DataFrame()

        if len(non_empty) == 1:
            return non_empty[0]

        result = pd.concat(non_empty, ignore_index=ignore_index, verify_integrity=verify_integrity)
        return result

    def join_datasets(
        self, datasets: List[pd.DataFrame], on: Union[str, List[str]] = None, how: str = "inner"
    ) -> pd.DataFrame:
        """
        水平连接多个数据集（按列连接），常用于合并不同来源的同时间数据
        Args:
            datasets: DataFrame列表
            on: 连接键，必须是所有数据集都有的列
            how: 连接方式
        Returns:
            连接后的DataFrame
        """
        if len(datasets) < 2:
            return datasets[0] if datasets else pd.DataFrame()

        result = datasets[0]
        for i, df in enumerate(datasets[1:], 2):
            if df.empty:
                logger.warning(f"{self.name}: 第{i}个数据集为空，跳过")
                continue
            result = pd.merge(result, df, on=on, how=how, suffixes=(f"_{i-1}", f"_{i}"))

        return result

    def align_time_range(
        self,
        datasets: List[pd.DataFrame],
        time_col: str = "trade_date",
        intersection: bool = True,
        fill_missing: str = "ffill",
    ) -> List[pd.DataFrame]:
        """
        对齐多个数据集的时间范围，使所有数据集覆盖相同的时间区间
        Args:
            datasets: DataFrame列表，每个必须包含时间列
            time_col: 时间列名
            intersection: True取交集，False取并集
            fill_missing: 缺失值填充方法，'ffill', 'bfill', 'drop', None不填充
        Returns:
            对齐后的数据集列表
        """
        aligned_datasets = []
        all_timestamps = []

        # 收集所有时间戳并转换
        for i, df in enumerate(datasets):
            if df.empty:
                logger.warning(f"{self.name}: 第{i+1}个数据集为空")
                aligned_datasets.append(df)
                continue

            df = df.copy()
            df[time_col] = pd.to_datetime(df[time_col])
            df = df.sort_values(time_col).reset_index(drop=True)
            aligned_datasets.append(df)
            all_timestamps.extend(df[time_col].unique())

        if intersection:
            # 取交集 - 所有数据集都包含的时间
            common_timestamps = set(aligned_datasets[0][time_col].unique())
            for df in aligned_datasets[1:]:
                common_timestamps.intersection_update(set(df[time_col].unique()))
            target_dates = sorted(common_timestamps)
        else:
            # 取并集 - 所有时间的并集
            target_dates = sorted(set(all_timestamps))

        if not target_dates:
            logger.warning(f"{self.name}: 没有共同的时间戳")
            return aligned_datasets

        # 对齐每个数据集到目标时间
        result_datasets = []
        for df in aligned_datasets:
            if df.empty:
                result_datasets.append(df)
                continue

            # 设置时间索引
            df = df.set_index(time_col)
            # 重新索引到目标时间
            df_aligned = df.reindex(target_dates)

            # 填充缺失值
            if fill_missing == "ffill":
                df_aligned = df_aligned.ffill()
            elif fill_missing == "bfill":
                df_aligned = df_aligned.bfill()
            elif fill_missing == "drop":
                df_aligned = df_aligned.dropna()

            # 恢复时间列
            df_aligned = df_aligned.reset_index()
            df_aligned = df_aligned.rename(columns={"index": time_col})

            result_datasets.append(df_aligned)

        return result_datasets

    def merge_by_date_and_code(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        code_col: str = "ts_code",
        date_col: str = "trade_date",
        how: str = "left",
        suffixes: tuple = ("_left", "_right"),
    ) -> pd.DataFrame:
        """
        通用的按股票代码+日期合并
        Args:
            left_df: 左侧DataFrame
            right_df: 右侧DataFrame
            code_col: 股票代码列
            date_col: 日期列
            how: 连接方式
            suffixes: 后缀
        Returns:
            合并后的DataFrame
        """
        left_df = left_df.copy()
        right_df = right_df.copy()

        # 统一日期格式
        left_df[date_col] = pd.to_datetime(left_df[date_col])
        right_df[date_col] = pd.to_datetime(right_df[date_col])

        merged = pd.merge(left_df, right_df, on=[code_col, date_col], how=how, suffixes=suffixes)

        # 排序
        merged = merged.sort_values([code_col, date_col]).reset_index(drop=True)

        return merged
