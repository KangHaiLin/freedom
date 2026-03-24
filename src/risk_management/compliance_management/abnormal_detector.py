"""
异常交易检测
识别异常交易模式，满足反洗钱和监管要求
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd


class AbnormalTradeDetector:
    """
    异常交易检测器
    识别各类异常交易模式：
    - 大额频繁交易
    - 快进快出
    - 对敲交易
    - 分单申报
    - 尾市拉抬打压
    """

    def __init__(
        self,
        large_order_threshold: float = 1000000,
        frequent_daily_threshold: int = 10,
        holding_days_threshold: int = 1,
    ):
        """
        初始化检测器

        Args:
            large_order_threshold: 大额订单阈值（金额）
            frequent_daily_threshold: 每日频繁交易阈值（笔数）
            holding_days_threshold: 快进快出持仓天数阈值
        """
        self._large_order_threshold = large_order_threshold
        self._frequent_daily_threshold = frequent_daily_threshold
        self._holding_days_threshold = holding_days_threshold

    def detect_large_order(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测大额订单

        Args:
            trades: 交易列表

        Returns:
            异常交易列表
        """
        anomalies = []
        for trade in trades:
            amount = trade.get("price", 0.0) * trade.get("quantity", 0)
            if amount >= self._large_order_threshold:
                anomalies.append(
                    {
                        "type": "large_order",
                        "trade_id": trade.get("trade_id"),
                        "amount": amount,
                        "threshold": self._large_order_threshold,
                        "trade_data": trade,
                    }
                )
        return anomalies

    def detect_frequent_trading(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测单日频繁交易

        Args:
            trades: 交易列表

        Returns:
            异常列表，按日期分组
        """
        if not trades:
            return []

        # 按日期分组
        df = pd.DataFrame(trades)
        df["date"] = pd.to_datetime(df.get("filled_time", datetime.now())).dt.date
        daily_counts = df.groupby("date").size()

        anomalies = []
        for date, count in daily_counts.items():
            if count >= self._frequent_daily_threshold:
                daily_trades = df[df["date"] == date].to_dict("records")
                anomalies.append(
                    {
                        "type": "frequent_daily",
                        "date": date.isoformat(),
                        "count": count,
                        "threshold": self._frequent_daily_threshold,
                        "trades": daily_trades,
                    }
                )
        return anomalies

    def detect_fast_in_out(self, trades: List[Dict[str, Any]], positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测快进快出（持仓时间过短）

        Args:
            trades: 交易列表
            positions: 持仓列表

        Returns:
            异常列表
        """
        anomalies = []

        # 对每只股票计算买入卖出间隔
        for ts_code in set(t.get("ts_code") for t in trades):
            code_trades = [t for t in trades if t.get("ts_code") == ts_code]
            code_trades.sort(key=lambda x: x.get("filled_time", datetime.min))

            buy_time = None
            for trade in code_trades:
                if trade.get("side") == "BUY":
                    buy_time = datetime.fromisoformat(str(trade.get("filled_time")))
                elif trade.get("side") == "SELL" and buy_time:
                    sell_time = datetime.fromisoformat(str(trade.get("filled_time")))
                    holding_days = (sell_time - buy_time).days
                    if holding_days <= self._holding_days_threshold:
                        anomalies.append(
                            {
                                "type": "fast_in_out",
                                "ts_code": ts_code,
                                "holding_days": holding_days,
                                "threshold": self._holding_days_threshold,
                                "buy_time": buy_time.isoformat(),
                                "sell_time": sell_time.isoformat(),
                            }
                        )
                    buy_time = None
        return anomalies

    def detect_price_manipulation(
        self,
        intraday_data: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        """
        检测价格操纵（尾市拉抬/打压）

        Args:
            intraday_data: 分钟K线数据，必须包含time, price, volume

        Returns:
            异常列表
        """
        anomalies = []

        if len(intraday_data) < 10:
            return anomalies

        # 获取最后15分钟
        last_15 = intraday_data.iloc[-15:]
        price_change = (last_15.iloc[-1]["close"] - last_15.iloc[0]["open"]) / last_15.iloc[0]["open"]

        # 尾市涨幅超过2%且放量，可能拉抬
        if price_change > 0.02:
            volume_ratio = last_15["volume"].mean() / intraday_data.iloc[:-15]["volume"].mean()
            if volume_ratio > 2:
                anomalies.append(
                    {
                        "type": "end_of_day_ramp",
                        "price_change": price_change * 100,
                        "volume_ratio": volume_ratio,
                        "description": "尾市大幅拉抬配合放量，疑似价格操纵",
                    }
                )

        # 尾市跌幅超过2%且放量，可能打压
        if price_change < -0.02:
            volume_ratio = last_15["volume"].mean() / intraday_data.iloc[:-15]["volume"].mean()
            if volume_ratio > 2:
                anomalies.append(
                    {
                        "type": "end_of_day_suppress",
                        "price_change": price_change * 100,
                        "volume_ratio": volume_ratio,
                        "description": "尾市大幅打压配合放量，疑似价格操纵",
                    }
                )

        return anomalies

    def detect_splitting_orders(
        self,
        orders: List[Dict[str, Any]],
        window_minutes: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        检测分单申报（大单拆成多个小单）

        Args:
            orders: 订单列表
            window_minutes: 时间窗口（分钟）

        Returns:
            异常列表
        """
        if len(orders) < 3:
            return []

        anomalies = []
        df = pd.DataFrame(orders)
        df["datetime"] = pd.to_datetime(df.get("created_at", datetime.now()))

        # 按股票代码和方向分组
        for (ts_code, side), group in df.groupby(["ts_code", "side"]):
            if len(group) < 3:
                continue
            # 按时间排序
            group = group.sort_values("datetime")
            # 滑动窗口检查短时间内多笔同方向订单
            for i in range(len(group) - 2):
                window = group.iloc[i : i + 3]
                time_diff = (window.iloc[-1]["datetime"] - window.iloc[0]["datetime"]).total_seconds()
                if time_diff <= window_minutes * 60:
                    # 短时间内多笔，检查总金额是否达到大额标准
                    total_amount = (window["price"] * window["quantity"]).sum()
                    if total_amount >= self._large_order_threshold * 0.8:
                        # 大单拆分检测到
                        anomalies.append(
                            {
                                "type": "splitting_orders",
                                "ts_code": ts_code,
                                "side": side,
                                "order_count": 3,
                                "total_amount": total_amount,
                                "time_span_seconds": time_diff,
                                "description": f"{time_diff:.0f}秒内分3笔申报，总金额接近大额阈值",
                            }
                        )
        return anomalies

    def detect_all(
        self,
        trades: List[Dict[str, Any]],
        positions: Optional[List[Dict[str, Any]]] = None,
        intraday_data: Optional[pd.DataFrame] = None,
        orders: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        执行所有异常检测

        Returns:
            检测结果汇总
        """
        results = {}
        results["large_order"] = self.detect_large_order(trades)
        results["frequent_trading"] = self.detect_frequent_trading(trades)
        if positions is not None:
            results["fast_in_out"] = self.detect_fast_in_out(trades, positions)
        if intraday_data is not None:
            results["price_manipulation"] = self.detect_price_manipulation(intraday_data)
        if orders is not None:
            results["splitting_orders"] = self.detect_splitting_orders(orders)

        # 统计
        total_anomalies = sum(len(v) for v in results.values())

        return {
            "results": results,
            "total_anomalies": total_anomalies,
            "has_anomalies": total_anomalies > 0,
        }

    def set_thresholds(
        self,
        large_order_threshold: Optional[float] = None,
        frequent_daily_threshold: Optional[int] = None,
        holding_days_threshold: Optional[int] = None,
    ) -> None:
        """设置检测阈值"""
        if large_order_threshold is not None:
            self._large_order_threshold = large_order_threshold
        if frequent_daily_threshold is not None:
            self._frequent_daily_threshold = frequent_daily_threshold
        if holding_days_threshold is not None:
            self._holding_days_threshold = holding_days_threshold
