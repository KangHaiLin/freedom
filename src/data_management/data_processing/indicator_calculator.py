"""
技术指标和基本面指标计算器
计算A股常用技术指标：SMA、EMA、RSI、KDJ、MACD、BOLL、VWAP、OBV、ADX
以及基本面衍生指标：PE衍生、PB衍生、ROE衍生、同比环比增长率
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from common.utils import NumberUtils

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class IndicatorCalculator(BaseProcessor):
    """技术指标和基本面指标计算器"""

    def __init__(self, config: Dict = None):
        super().__init__(config=config)
        # 默认参数配置
        self.default_params = self.config.get(
            "default_params",
            {
                "sma": {"windows": [5, 10, 20, 60]},
                "ema": {"windows": [12, 26]},
                "rsi": {"window": 14},
                "kdj": {"n": 9, "m1": 3, "m2": 3},
                "macd": {"fast": 12, "slow": 26, "signal": 9},
                "boll": {"window": 20, "std_dev": 2},
                "adx": {"window": 14},
            },
        )

    def process(self, data: Any, indicators: Optional[List[str]] = None, **kwargs) -> pd.DataFrame:
        """
        批量计算指定的技术指标
        Args:
            data: 输入DataFrame，必须包含open, high, low, close, volume列
            indicators: 需要计算的指标列表，None计算全部默认指标
            **kwargs: 自定义参数
        Returns:
            添加了指标列的DataFrame
        """
        if not self.validate_input(data):
            logger.warning(f"{self.name}: 输入数据验证失败")
            return data

        if not isinstance(data, pd.DataFrame):
            logger.warning(f"{self.name}: 输入必须是DataFrame")
            return data

        df = data.copy()
        indicators = indicators or ["sma", "ema", "rsi", "kdj", "macd", "boll", "vwap", "obv", "adx"]

        for indicator in indicators:
            try:
                if indicator == "sma":
                    df = self.calculate_sma(df, **kwargs.get("sma", {}))
                elif indicator == "ema":
                    df = self.calculate_ema(df, **kwargs.get("ema", {}))
                elif indicator == "rsi":
                    df = self.calculate_rsi(df, **kwargs.get("rsi", {}))
                elif indicator == "kdj":
                    df = self.calculate_kdj(df, **kwargs.get("kdj", {}))
                elif indicator == "macd":
                    df = self.calculate_macd(df, **kwargs.get("macd", {}))
                elif indicator == "boll":
                    df = self.calculate_boll(df, **kwargs.get("boll", {}))
                elif indicator == "vwap":
                    df = self.calculate_vwap(df)
                elif indicator == "obv":
                    df = self.calculate_obv(df)
                elif indicator == "adx":
                    df = self.calculate_adx(df, **kwargs.get("adx", {}))
                else:
                    logger.warning(f"{self.name}: 未知的指标类型: {indicator}")
            except Exception as e:
                logger.error(f"{self.name}: 计算{indicator}失败: {e}")

        return df

    def calculate_sma(self, df: pd.DataFrame, windows: List[int] = None, close_col: str = "close") -> pd.DataFrame:
        """
        计算简单移动平均 (Simple Moving Average)
        Args:
            df: 输入DataFrame
            windows: 窗口大小列表
            close_col: 收盘价列名
        Returns:
            添加了sma列的DataFrame
        """
        windows = windows or self.default_params["sma"]["windows"]
        df = df.copy()

        if close_col not in df.columns:
            logger.warning(f"{self.name}: 缺少{close_col}列，跳过SMA计算")
            return df

        for window in windows:
            df[f"sma_{window}"] = df[close_col].rolling(window=window).mean()
            df[f"sma_{window}"] = df[f"sma_{window}"].apply(NumberUtils.round_price).astype(float)

        return df

    def calculate_ema(self, df: pd.DataFrame, windows: List[int] = None, close_col: str = "close") -> pd.DataFrame:
        """
        计算指数移动平均 (Exponential Moving Average)
        Args:
            df: 输入DataFrame
            windows: 窗口大小列表
            close_col: 收盘价列名
        Returns:
            添加了ema列的DataFrame
        """
        windows = windows or self.default_params["ema"]["windows"]
        df = df.copy()

        if close_col not in df.columns:
            logger.warning(f"{self.name}: 缺少{close_col}列，跳过EMA计算")
            return df

        for window in windows:
            df[f"ema_{window}"] = df[close_col].ewm(span=window, adjust=False).mean()
            df[f"ema_{window}"] = df[f"ema_{window}"].apply(NumberUtils.round_price).astype(float)

        return df

    def calculate_rsi(self, df: pd.DataFrame, window: int = None, close_col: str = "close") -> pd.DataFrame:
        """
        计算相对强弱指数 (Relative Strength Index)
        公式: RSI = 100 - 100 / (1 + RS), RS = 平均涨幅 / 平均跌幅
        Args:
            df: 输入DataFrame
            window: 窗口大小，默认14
            close_col: 收盘价列名
        Returns:
            添加了rsi列的DataFrame
        """
        window = window or self.default_params["rsi"]["window"]
        df = df.copy()

        if close_col not in df.columns:
            logger.warning(f"{self.name}: 缺少{close_col}列，跳过RSI计算")
            return df

        # 计算价格变化
        delta = df[close_col].diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        # 计算平均涨跌
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        # 计算RS和RSI
        rs = avg_gain / avg_loss
        df[f"rsi_{window}"] = (100 - (100 / (1 + rs))).round(2)

        return df

    def calculate_kdj(
        self,
        df: pd.DataFrame,
        n: int = None,
        m1: int = None,
        m2: int = None,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
    ) -> pd.DataFrame:
        """
        计算KDJ指标
        公式: RSV = (收盘价 - N日最低) / (N日最高 - N日最低) * 100
              K = 2/3 * 前一日K + 1/3 * RSV
              D = 2/3 * 前一日D + 1/3 * K
              J = 3*K - 2*D
        Args:
            df: 输入DataFrame
            n: RSV周期，默认9
            m1: K周期，默认3
            m2: D周期，默认3
        Returns:
            添加了k, d, j列的DataFrame
        """
        n = n or self.default_params["kdj"]["n"]
        m1 = m1 or self.default_params["kdj"]["m1"]
        m2 = m2 or self.default_params["kdj"]["m2"]
        df = df.copy()

        for col in [high_col, low_col, close_col]:
            if col not in df.columns:
                logger.warning(f"{self.name}: 缺少{col}列，跳过KDJ计算")
                return df

        # 计算N周期最低最低价和最高最高价
        low_n = df[low_col].rolling(window=n).min()
        high_n = df[high_col].rolling(window=n).max()

        # 计算RSV
        rsv = (df[close_col] - low_n) / (high_n - low_n) * 100
        rsv = rsv.fillna(50)

        # 计算K, D, J
        k = pd.Series(index=df.index, dtype=float)
        d = pd.Series(index=df.index, dtype=float)

        k.iloc[0] = 50
        d.iloc[0] = 50

        for i in range(1, len(df)):
            k.iloc[i] = (1 / m1) * rsv.iloc[i] + ((m1 - 1) / m1) * k.iloc[i - 1]
            d.iloc[i] = (1 / m2) * k.iloc[i] + ((m2 - 1) / m2) * d.iloc[i - 1]

        j = 3 * k - 2 * d

        df[f"k_{n}"] = k.round(2)
        df[f"d_{n}"] = d.round(2)
        df[f"j_{n}"] = j.round(2)

        return df

    def calculate_macd(
        self, df: pd.DataFrame, fast: int = None, slow: int = None, signal: int = None, close_col: str = "close"
    ) -> pd.DataFrame:
        """
        计算MACD指标
        公式: DIF = 短期EMA - 长期EMA
              DEA = DIF的EMA
              MACD柱 = 2 * (DIF - DEA)
        Args:
            df: 输入DataFrame
            fast: 快速EMA周期，默认12
            slow: 慢速EMA周期，默认26
            signal: 信号周期，默认9
        Returns:
            添加了dif, dea, macd柱状图列的DataFrame
        """
        fast = fast or self.default_params["macd"]["fast"]
        slow = slow or self.default_params["macd"]["slow"]
        signal = signal or self.default_params["macd"]["signal"]
        df = df.copy()

        if close_col not in df.columns:
            logger.warning(f"{self.name}: 缺少{close_col}列，跳过MACD计算")
            return df

        # 计算快慢EMA
        ema_fast = df[close_col].ewm(span=fast, adjust=False).mean()
        ema_slow = df[close_col].ewm(span=slow, adjust=False).mean()

        # 计算DIF和DEA
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_bar = 2 * (dif - dea)

        df["macd_dif"] = dif.round(4)
        df["macd_dea"] = dea.round(4)
        df["macd_bar"] = macd_bar.round(4)

        return df

    def calculate_boll(
        self, df: pd.DataFrame, window: int = None, std_dev: int = None, close_col: str = "close"
    ) -> pd.DataFrame:
        """
        计算布林带 (Bollinger Bands)
        公式: 中轨 = SMA
              上轨 = 中轨 + N倍标准差
              下轨 = 中轨 - N倍标准差
        Args:
            df: 输入DataFrame
            window: 窗口大小，默认20
            std_dev: 标准差倍数，默认2
        Returns:
            添加了布林带三轨的DataFrame
        """
        window = window or self.default_params["boll"]["window"]
        std_dev = std_dev or self.default_params["boll"]["std_dev"]
        df = df.copy()

        if close_col not in df.columns:
            logger.warning(f"{self.name}: 缺少{close_col}列，跳过BOLL计算")
            return df

        # 计算中轨和标准差
        middle = df[close_col].rolling(window=window).mean()
        std = df[close_col].rolling(window=window).std()

        df[f"boll_mid_{window}"] = middle.apply(NumberUtils.round_price).astype(float)
        df[f"boll_up_{window}"] = (middle + std_dev * std).apply(NumberUtils.round_price).astype(float)
        df[f"boll_down_{window}"] = (middle - std_dev * std).apply(NumberUtils.round_price).astype(float)

        return df

    def calculate_vwap(
        self,
        df: pd.DataFrame,
        close_col: str = "close",
        volume_col: str = "volume",
        group_by_date: bool = True,
        date_col: str = "trade_date",
    ) -> pd.DataFrame:
        """
        计算成交量加权平均价格 (Volume Weighted Average Price)
        Args:
            df: 输入DataFrame，按时间排序
            close_col: 价格列名
            volume_col: 成交量列名
            group_by_date: 是否按日期分组计算（日内分时数据需要）
            date_col: 日期列名
        Returns:
            添加了vwap列的DataFrame
        """
        df = df.copy()
        df = df.sort_index()

        if close_col not in df.columns or volume_col not in df.columns:
            logger.warning(f"{self.name}: 缺少价格或成交量列，跳过VWAP计算")
            return df

        if group_by_date and date_col in df.columns:
            # 按日期分组计算累计VWAP
            df["cum_price_vol"] = (df[close_col] * df[volume_col]).groupby(df[date_col]).cumsum()
            df["cum_volume"] = df[volume_col].groupby(df[date_col]).cumsum()
            df["vwap"] = (df["cum_price_vol"] / df["cum_volume"]).apply(NumberUtils.round_price).astype(float)
            df = df.drop(["cum_price_vol", "cum_volume"], axis=1)
        else:
            # 全局累计VWAP
            cum_price_vol = (df[close_col] * df[volume_col]).cumsum()
            cum_volume = df[volume_col].cumsum()
            df["vwap"] = (cum_price_vol / cum_volume).apply(NumberUtils.round_price)

        return df

    def calculate_obv(self, df: pd.DataFrame, close_col: str = "close", volume_col: str = "volume") -> pd.DataFrame:
        """
        计算能量潮 (On-Balance Volume)
        公式: 收盘价上涨 -> OBV += 成交量; 收盘价下跌 -> OBV -= 成交量
        Args:
            df: 输入DataFrame，按时间排序
            close_col: 收盘价列名
            volume_col: 成交量列名
        Returns:
            添加了obv列的DataFrame
        """
        df = df.copy()

        if close_col not in df.columns or volume_col not in df.columns:
            logger.warning(f"{self.name}: 缺少价格或成交量列，跳过OBV计算")
            return df

        # 计算价格变化方向
        delta = df[close_col].diff()
        obv = df[volume_col].copy()
        obv[delta < 0] = -obv[delta < 0]

        df["obv"] = obv.cumsum()

        return df

    def calculate_adx(
        self,
        df: pd.DataFrame,
        window: int = None,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
    ) -> pd.DataFrame:
        """
        计算平均趋向指数 (Average Directional Index)
        Args:
            df: 输入DataFrame
            window: 窗口大小，默认14
        Returns:
            添加了adx列的DataFrame
        """
        window = window or self.default_params["adx"]["window"]
        df = df.copy()

        for col in [high_col, low_col, close_col]:
            if col not in df.columns:
                logger.warning(f"{self.name}: 缺少{col}列，跳过ADX计算")
                return df

        # 计算+DM和-DM
        high_diff = df[high_col].diff()
        low_diff = df[low_col].diff().abs()

        plus_dm = high_diff.where(high_diff > 0, 0)
        minus_dm = low_diff.where(low_diff > high_diff, 0)

        # 计算真实波动范围TR
        tr1 = df[high_col] - df[low_col]
        tr2 = (df[high_col] - df[close_col].shift()).abs()
        tr3 = (df[low_col] - df[close_col].shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 平滑计算
        atr = tr.rolling(window=window).mean()
        plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)

        # 计算DX和ADX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        adx = dx.rolling(window=window).mean()

        df[f"adx_{window}"] = adx.round(2)
        df[f"plus_di_{window}"] = plus_di.round(2)
        df[f"minus_di_{window}"] = minus_di.round(2)

        return df

    def calculate_fundamental_derivatives(
        self,
        df: pd.DataFrame,
        pe_col: str = "pe",
        pb_col: str = "pb",
        roe_col: str = "roe",
        earnings_col: str = "net_profit",
        revenue_col: str = "revenue",
    ) -> pd.DataFrame:
        """
        计算基本面衍生指标
        - PE百分位
        - PB百分位
        - ROE分档
        - 同比增长率
        - 环比增长率
        Args:
            df: 输入DataFrame，按时间排序
        Returns:
            添加衍生指标的DataFrame
        """
        df = df.copy()

        if pe_col in df.columns:
            df["pe_percentile"] = df[pe_col].rank(pct=True).round(4)

        if pb_col in df.columns:
            df["pb_percentile"] = df[pb_col].rank(pct=True).round(4)

        if roe_col in df.columns:
            df["roe_rank"] = pd.qcut(df[roe_col], q=5, labels=["1", "2", "3", "4", "5"])

        if earnings_col in df.columns:
            # 同比增长率 = 本期 / 去年同期 - 1
            df["earnings_yoy"] = (
                (df[earnings_col] / df[earnings_col].shift(4) - 1)
                if "quarter" in df.columns
                else (df[earnings_col] / df[earnings_col].shift(1) - 1)
            ).round(4)
            # 环比增长率 = 本期 / 上期 - 1
            df["earnings_qoq"] = ((df[earnings_col] / df[earnings_col].shift(1)) - 1).round(4)

        if revenue_col in df.columns:
            df["revenue_yoy"] = (
                (df[revenue_col] / df[revenue_col].shift(4) - 1)
                if "quarter" in df.columns
                else (df[revenue_col] / df[revenue_col].shift(1) - 1)
            ).round(4)
            df["revenue_qoq"] = ((df[revenue_col] / df[revenue_col].shift(1)) - 1).round(4)

        return df
