"""
实时流处理器
负责增量处理、滑动窗口维护、实时指标计算、过期数据自动清理
"""

import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from .base_processor import BaseProcessor
from .indicator_calculator import IndicatorCalculator

logger = logging.getLogger(__name__)


class StreamProcessor(BaseProcessor):
    """实时流处理器，维护滑动窗口，增量计算指标"""

    def __init__(
        self, config: Dict = None, window_size: int = None, max_records: int = None, keep_raw_data: bool = None
    ):
        super().__init__(config=config)
        # 滑动窗口大小
        self.window_size = window_size if window_size is not None else self.config.get("window_size", 100)
        # 数据保留最大条数，超过自动清理
        self.max_records = max_records if max_records is not None else self.config.get("max_records", 10000)
        # 是否保留原始数据
        self.keep_raw_data = keep_raw_data if keep_raw_data is not None else self.config.get("keep_raw_data", True)

        # 存储每个股票的滑动窗口数据，使用OrderedDict维护顺序
        self.stock_data: Dict[str, OrderedDict] = OrderedDict()
        # 存储实时计算的指标
        self.stock_indicators: Dict[str, Dict] = {}

        # 指标计算器
        self.indicator_calculator = IndicatorCalculator()

    def process(self, data: Union[Dict, List[Dict]], **kwargs) -> Dict[str, Any]:
        """
        增量处理新到达的数据
        Args:
            data: 单条数据字典或多条数据列表，必须包含ts_code和trade_time/trade_date
        Returns:
            处理结果，包含最新指标值
        """
        import time

        start_time = time.time()

        if isinstance(data, dict):
            data = [data]

        results = {}
        for item in data:
            try:
                ts_code = item.get("ts_code")
                if not ts_code:
                    logger.warning(f"{self.name}: 数据缺少ts_code，跳过")
                    continue

                # 添加到滑动窗口
                self._add_to_window(ts_code, item)

                # 计算实时指标
                indicators = self._calculate_realtime_indicators(ts_code)
                results[ts_code] = indicators

                # 更新最新指标
                self.stock_indicators[ts_code] = indicators

                # 清理过期数据
                self._cleanup_expired()

            except Exception as e:
                logger.error(f"{self.name}: 处理流数据失败: {e}")

        self._record_processing(start_time)

        return {
            "success": True,
            "results": results,
            "processed_count": len(data),
            "processing_time": time.time() - start_time,
        }

    def _add_to_window(self, ts_code: str, data: Dict):
        """添加数据到滑动窗口"""
        if ts_code not in self.stock_data:
            self.stock_data[ts_code] = OrderedDict()

        # 获取时间键
        time_key = data.get("trade_time") or data.get("trade_date") or len(self.stock_data[ts_code])

        # 添加数据，如果已存在则覆盖
        self.stock_data[ts_code][time_key] = data

        # 如果超过窗口大小，删除最旧的
        if len(self.stock_data[ts_code]) > self.window_size:
            # 删除第一个元素（最旧）
            first_key = next(iter(self.stock_data[ts_code]))
            del self.stock_data[ts_code][first_key]

    def _calculate_realtime_indicators(self, ts_code: str) -> Dict:
        """计算最新的实时指标"""
        window_df = self.get_stock_window(ts_code)
        if window_df is None or len(window_df) < 5:
            # 数据不足，只返回原始价格
            latest = self.get_latest(ts_code)
            return {"latest_price": latest.get("close", None) if latest else None, "sma_5": None, "rsi_14": None}

        # 使用指标计算器计算
        indicators_df = self.indicator_calculator.process(window_df, indicators=["sma", "rsi", "macd"])

        # 获取最新一行的指标值
        latest_row = indicators_df.iloc[-1]
        result = {}

        # 收集所有指标列
        for col in indicators_df.columns:
            if col.startswith(("sma_", "ema_", "rsi_", "k_", "d_", "j_", "macd_", "boll_", "adx_")):
                result[col] = latest_row[col] if not pd.isna(latest_row[col]) else None

        # 添加最新价格
        if "close" in latest_row:
            result["latest_price"] = latest_row["close"]

        return result

    def get_stock_window(self, ts_code: str) -> Optional[pd.DataFrame]:
        """获取指定股票的当前滑动窗口数据"""
        if ts_code not in self.stock_data:
            return None

        data_list = list(self.stock_data[ts_code].values())
        return pd.DataFrame(data_list)

    def get_latest(self, ts_code: str) -> Optional[Dict]:
        """获取指定股票的最新一条数据"""
        if ts_code not in self.stock_data:
            return None

        # OrderedDict最后一个就是最新的
        last_key = next(reversed(self.stock_data[ts_code]))
        return self.stock_data[ts_code][last_key]

    def get_latest_indicators(self, ts_code: str = None) -> Optional[Dict]:
        """获取最新计算的指标"""
        if ts_code:
            return self.stock_indicators.get(ts_code)
        else:
            # 返回所有股票最新指标
            return self.stock_indicators.copy()

    def get_recent_klines(self, ts_code: str, count: int = 20) -> Optional[pd.DataFrame]:
        """获取最近N根K线"""
        df = self.get_stock_window(ts_code)
        if df is None:
            return None

        return df.tail(count)

    def set_window_size(self, size: int):
        """设置滑动窗口大小"""
        self.window_size = size
        # 对已有数据进行裁剪
        for ts_code in self.stock_data:
            data = self.stock_data[ts_code]
            if len(data) > size:
                # 删除多余的最旧数据
                keys = list(data.keys())[:-size]
                for key in keys:
                    del data[key]
        logger.info(f"{self.name}: 窗口大小已更新为{size}")

    def clear_stock(self, ts_code: str):
        """清除指定股票的数据"""
        if ts_code in self.stock_data:
            del self.stock_data[ts_code]
        if ts_code in self.stock_indicators:
            del self.stock_indicators[ts_code]
        logger.info(f"{self.name}: 已清除股票{ts_code}数据")

    def clear_all(self):
        """清除所有数据"""
        self.stock_data.clear()
        self.stock_indicators.clear()
        logger.info(f"{self.name}: 已清除所有数据")

    def _cleanup_expired(self):
        """清理过期数据，当总记录数超过max_records时"""
        if len(self.stock_data) > self.max_records:
            # 移除最旧的股票数据（OrderedDict保持插入顺序）
            oldest_keys = list(self.stock_data.keys())[: int(self.max_records * 0.1)]
            for key in oldest_keys:
                self.clear_stock(key)
            logger.info(f"{self.name}: 清理了{len(oldest_keys)}个过期股票数据")

    def get_statistics(self) -> Dict:
        """获取当前流处理器统计信息"""
        total_records = sum(len(window) for window in self.stock_data.values())
        return {
            "stock_count": len(self.stock_data),
            "total_records": total_records,
            "max_records_config": self.max_records,
            "window_size_config": self.window_size,
            "indicators_count": len(self.stock_indicators),
        }

    def get_all_stocks(self) -> List[str]:
        """获取当前所有有数据的股票代码"""
        return list(self.stock_data.keys())
