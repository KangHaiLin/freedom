"""
数据清洗处理器
负责对采集到的原始数据进行清洗、标准化、异常值处理
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from common.constants import DEFAULT_QUALITY_RULES, BusinessConstants
from common.exceptions import DataValidationException
from common.utils import DateTimeUtils, NumberUtils, StockCodeUtils

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗处理器"""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        # 异常值过滤阈值
        self.price_change_threshold = self.config.get(
            "price_change_threshold", DEFAULT_QUALITY_RULES["price_change_threshold"]
        )  # 价格涨跌幅超过20%标记为异常
        self.volume_change_threshold = self.config.get(
            "volume_change_threshold", DEFAULT_QUALITY_RULES["volume_change_threshold"]
        )  # 成交量超过均值10倍标记为异常
        self.enable_outlier_detection = self.config.get(
            "enable_outlier_detection", DEFAULT_QUALITY_RULES["outlier_detection_enabled"]
        )
        self.enable_missing_value_fill = self.config.get(
            "enable_missing_value_fill", DEFAULT_QUALITY_RULES["missing_value_fill_enabled"]
        )
        self.enable_duplicate_removal = self.config.get(
            "enable_duplicate_removal", DEFAULT_QUALITY_RULES["duplicate_removal_enabled"]
        )

    def clean_realtime_quote(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗实时行情数据
        Args:
            df: 原始实时行情数据
        Returns:
            清洗后的行情数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            # 1. 去重
            if self.enable_duplicate_removal:
                before_count = len(df)
                df = df.drop_duplicates(subset=["stock_code", "time"], keep="last")
                after_count = len(df)
                if before_count != after_count:
                    logger.debug(f"实时行情去重，移除{before_count - after_count}条重复数据")

            # 2. 数据类型转换
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            if "open" in df.columns:
                df["open"] = pd.to_numeric(df["open"], errors="coerce")
            if "high" in df.columns:
                df["high"] = pd.to_numeric(df["high"], errors="coerce")
            if "low" in df.columns:
                df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")
            if "amount" in df.columns:
                df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            if "bid_price1" in df.columns:
                df["bid_price1"] = pd.to_numeric(df["bid_price1"], errors="coerce")
            if "bid_volume1" in df.columns:
                df["bid_volume1"] = pd.to_numeric(df["bid_volume1"], errors="coerce").astype("Int64")
            if "ask_price1" in df.columns:
                df["ask_price1"] = pd.to_numeric(df["ask_price1"], errors="coerce")
            if "ask_volume1" in df.columns:
                df["ask_volume1"] = pd.to_numeric(df["ask_volume1"], errors="coerce").astype("Int64")

            # 3. 缺失值处理
            if self.enable_missing_value_fill:
                # 价格缺失的用最近价格填充
                df["price"] = df.groupby("stock_code")["price"].ffill()
                # 成交量缺失填充0
                df["volume"] = df["volume"].fillna(0)
                if "amount" in df.columns:
                    df["amount"] = df["amount"].fillna(0)
                if "bid_volume1" in df.columns:
                    df["bid_volume1"] = df["bid_volume1"].fillna(0)
                if "ask_volume1" in df.columns:
                    df["ask_volume1"] = df["ask_volume1"].fillna(0)

            # 4. 异常值检测与处理
            if self.enable_outlier_detection:
                df = self._detect_and_handle_outliers(df, data_type="realtime")

            # 5. 标准化处理
            df["stock_code"] = df["stock_code"].apply(lambda x: StockCodeUtils.normalize_code(x))
            df["time"] = pd.to_datetime(df["time"]).dt.floor("s")  # 时间精确到秒
            df["price"] = df["price"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)
            if "bid_price1" in df.columns:
                df["bid_price1"] = df["bid_price1"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)
            if "ask_price1" in df.columns:
                df["ask_price1"] = df["ask_price1"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)

            # 6. 校验涨跌停限制
            df = self._validate_price_limit(df)

            # 7. 过滤无效数据
            df = df[df["price"] > 0]  # 价格必须大于0
            df = df[df["volume"] >= 0]  # 成交量不能为负

            logger.debug(f"实时行情清洗完成，原始数据{len(df)}条，清洗后剩余{len(df)}条")
            return df

        except Exception as e:
            logger.error(f"实时行情清洗失败：{e}")
            raise DataValidationException(f"实时行情清洗失败：{e}") from e

    def clean_daily_quote(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗日线行情数据
        Args:
            df: 原始日线行情数据
        Returns:
            清洗后的日线数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            # 1. 去重
            if self.enable_duplicate_removal:
                before_count = len(df)
                df = df.drop_duplicates(subset=["stock_code", "trade_date"], keep="last")
                after_count = len(df)
                if before_count != after_count:
                    logger.debug(f"日线行情去重，移除{before_count - after_count}条重复数据")

            # 2. 数据类型转换
            numeric_columns = ["open", "high", "low", "close", "volume", "amount", "adjust_factor"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # 3. 缺失值处理
            if self.enable_missing_value_fill:
                # 按股票代码分组填充缺失值
                for col in ["open", "high", "low", "close"]:
                    if col in df.columns:
                        df[col] = df.groupby("stock_code")[col].ffill()
                df["volume"] = df["volume"].fillna(0)
                if "amount" in df.columns:
                    df["amount"] = df["amount"].fillna(0)
                if "adjust_factor" in df.columns:
                    df["adjust_factor"] = df["adjust_factor"].fillna(1.0)

            # 4. 异常值处理
            if self.enable_outlier_detection:
                df = self._detect_and_handle_outliers(df, data_type="daily")

            # 5. 标准化处理
            df["stock_code"] = df["stock_code"].apply(lambda x: StockCodeUtils.normalize_code(x))
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)
            if "adjust_factor" in df.columns:
                df["adjust_factor"] = df["adjust_factor"].apply(
                    lambda x: NumberUtils.round_ratio(x) if pd.notna(x) else x
                )

            # 6. 价格合理性校验
            df = df[df["high"] >= df["low"]]
            df = df[df["close"] >= df["low"]]
            df = df[df["close"] <= df["high"]]

            logger.debug(f"日线行情清洗完成，原始数据{len(df)}条，清洗后剩余{len(df)}条")
            return df

        except Exception as e:
            logger.error(f"日线行情清洗失败：{e}")
            raise DataValidationException(f"日线行情清洗失败：{e}") from e

    def clean_minute_quote(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗分钟线行情数据
        Args:
            df: 原始分钟线行情数据
        Returns:
            清洗后的分钟线数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            # 1. 去重
            if self.enable_duplicate_removal:
                before_count = len(df)
                df = df.drop_duplicates(subset=["stock_code", "trade_time"], keep="last")
                after_count = len(df)
                if before_count != after_count:
                    logger.debug(f"分钟线行情去重，移除{before_count - after_count}条重复数据")

            # 2. 数据类型转换
            numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 3. 缺失值处理
            if self.enable_missing_value_fill:
                for col in ["open", "high", "low", "close"]:
                    df[col] = df.groupby("stock_code")[col].ffill()
                df["volume"] = df["volume"].fillna(0)
                df["amount"] = df["amount"].fillna(0)

            # 4. 异常值处理
            if self.enable_outlier_detection:
                df = self._detect_and_handle_outliers(df, data_type="minute")

            # 5. 标准化处理
            df["stock_code"] = df["stock_code"].apply(lambda x: StockCodeUtils.normalize_code(x))
            df["trade_time"] = pd.to_datetime(df["trade_time"]).dt.floor("min")  # 时间精确到分钟
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col].apply(lambda x: NumberUtils.round_price(x))

            # 6. 价格合理性校验
            df = df[df["high"] >= df["low"]]

            logger.debug(f"分钟线行情清洗完成，原始数据{len(df)}条，清洗后剩余{len(df)}条")
            return df

        except Exception as e:
            logger.error(f"分钟线行情清洗失败：{e}")
            raise DataValidationException(f"分钟线行情清洗失败：{e}") from e

    def clean_tick_quote(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗Tick行情数据
        Args:
            df: 原始Tick行情数据
        Returns:
            清洗后的Tick数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            # 1. 去重
            if self.enable_duplicate_removal:
                before_count = len(df)
                df = df.drop_duplicates(subset=["stock_code", "trade_time", "price", "volume"], keep="last")
                after_count = len(df)
                if before_count != after_count:
                    logger.debug(f"Tick行情去重，移除{before_count - after_count}条重复数据")

            # 2. 数据类型转换
            numeric_columns = ["price", "volume", "amount", "bid_price1", "bid_volume1", "ask_price1", "ask_volume1"]
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 3. 缺失值处理
            df["volume"] = df["volume"].fillna(0)
            df["amount"] = df["amount"].fillna(0)
            df["bid_volume1"] = df["bid_volume1"].fillna(0)
            df["ask_volume1"] = df["ask_volume1"].fillna(0)

            # 4. 异常值处理
            if self.enable_outlier_detection:
                # Tick数据价格变化不能超过涨跌停
                df = self._validate_price_limit(df)

            # 5. 标准化处理
            df["stock_code"] = df["stock_code"].apply(lambda x: StockCodeUtils.normalize_code(x))
            df["trade_time"] = pd.to_datetime(df["trade_time"])
            df["price"] = df["price"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)
            if "bid_price1" in df.columns:
                df["bid_price1"] = df["bid_price1"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)
            if "ask_price1" in df.columns:
                df["ask_price1"] = df["ask_price1"].apply(lambda x: NumberUtils.round_price(x) if pd.notna(x) else x)

            logger.debug(f"Tick行情清洗完成，原始数据{len(df)}条，清洗后剩余{len(df)}条")
            return df

        except Exception as e:
            logger.error(f"Tick行情清洗失败：{e}")
            raise DataValidationException(f"Tick行情清洗失败：{e}") from e

    def _detect_and_handle_outliers(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        检测并处理异常值
        Args:
            df: 数据
            data_type: 数据类型：realtime/daily/minute/tick
        Returns:
            处理后的数据
        """
        if len(df) < 2:
            return df

        try:
            # 按股票代码分组处理
            def process_group(group):
                if len(group) < 2:
                    return group

                # 计算价格涨跌幅
                group["price_change"] = (
                    group["close"].pct_change().abs()
                    if data_type in ["daily", "minute"]
                    else group["price"].pct_change().abs()
                )

                # 计算成交量变化率
                avg_volume = group["volume"].rolling(window=min(20, len(group))).mean()
                group["volume_change"] = group["volume"] / avg_volume

                # 标记异常
                price_outlier = group["price_change"] > self.price_change_threshold
                volume_outlier = group["volume_change"] > self.volume_change_threshold

                # 处理异常值：价格异常用前值填充，成交量异常截断为均值的5倍
                group.loc[price_outlier, "close" if data_type in ["daily", "minute"] else "price"] = group[
                    "close" if data_type in ["daily", "minute"] else "price"
                ].shift(1)
                group.loc[volume_outlier, "volume"] = avg_volume * 5

                return group

            df = df.groupby("stock_code", group_keys=False).apply(process_group)

            # 移除辅助列
            if "price_change" in df.columns:
                df = df.drop(columns=["price_change"])
            if "volume_change" in df.columns:
                df = df.drop(columns=["volume_change"])

            return df

        except Exception as e:
            logger.warning(f"异常值检测处理失败：{e}")
            return df

    def _validate_price_limit(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        校验价格是否在涨跌停范围内
        Args:
            df: 行情数据
        Returns:
            校验后的数据，移除异常数据
        """
        try:
            # 这里简化处理，实际场景需要获取昨收盘价计算涨跌停范围
            # 目前只校验价格大于0，后续可以接入昨收数据完善
            df = df[df["price"] > 0]
            return df

        except Exception as e:
            logger.warning(f"涨跌停校验失败：{e}")
            return df

    def validate_data_quality(self, df: pd.DataFrame, data_type: str) -> Dict:
        """
        验证数据质量
        Args:
            df: 清洗后的数据
            data_type: 数据类型
        Returns:
            质量报告
        """
        if df.empty:
            return {
                "total_count": 0,
                "valid_count": 0,
                "completeness": 0.0,
                "accuracy": 0.0,
                "timeliness": 0.0,
                "quality_score": 0.0,
                "status": "failed",
            }

        total_count = len(df)
        valid_count = len(df.dropna())

        # 完整性
        completeness = valid_count / total_count

        # 准确性：检查价格合理性
        if "price" in df.columns:
            invalid_price = len(df[df["price"] <= 0])
            accuracy = (total_count - invalid_price) / total_count
        else:
            accuracy = 1.0

        # 时效性：检查最新数据时间
        now = DateTimeUtils.now()
        if "time" in df.columns:
            latest_time = df["time"].max()
            if isinstance(latest_time, str):
                latest_time = pd.to_datetime(latest_time)
            # 处理时区差异
            if latest_time.tzinfo is None and now.tzinfo is not None:
                latest_time = latest_time.tz_localize(now.tzinfo)
            elif latest_time.tzinfo is not None and now.tzinfo is None:
                now = now.tz_localize(latest_time.tzinfo)
            delay = (now - latest_time).total_seconds()
            timeliness = max(0, 1 - delay / DEFAULT_QUALITY_RULES["realtime_data_delay_max"])  # 实时数据延迟阈值
        elif "trade_time" in df.columns:
            latest_time = df["trade_time"].max()
            if isinstance(latest_time, str):
                latest_time = pd.to_datetime(latest_time)
            # 处理时区差异
            if latest_time.tzinfo is None and now.tzinfo is not None:
                latest_time = latest_time.tz_localize(now.tzinfo)
            elif latest_time.tzinfo is not None and now.tzinfo is None:
                now = now.tz_localize(latest_time.tzinfo)
            delay = (now - latest_time).total_seconds()
            timeliness = max(0, 1 - delay / DEFAULT_QUALITY_RULES["daily_data_delay_max"])  # 日线数据延迟阈值
        else:
            timeliness = 1.0

        quality_score = completeness * 0.4 + accuracy * 0.4 + timeliness * 0.2

        status = (
            "excellent"
            if quality_score >= DEFAULT_QUALITY_RULES["excellent_score_threshold"]
            else (
                "good"
                if quality_score >= DEFAULT_QUALITY_RULES["good_score_threshold"]
                else "poor" if quality_score >= DEFAULT_QUALITY_RULES["poor_score_threshold"] else "bad"
            )
        )

        return {
            "total_count": total_count,
            "valid_count": valid_count,
            "completeness": completeness,
            "accuracy": accuracy,
            "timeliness": timeliness,
            "quality_score": quality_score,
            "status": status,
        }


# 全局数据清洗实例
data_cleaner = DataCleaner()
