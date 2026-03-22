"""
数值处理工具类
提供金融数值计算、格式化、精度处理等功能
"""

import decimal
from typing import Optional, Union

import numpy as np


class NumberUtils:
    """数值处理工具类"""

    DECIMAL_PRECISION = 4  # 默认保留4位小数
    PRICE_PRECISION = 2  # 价格保留2位小数
    RATIO_PRECISION = 4  # 比率保留4位小数
    AMOUNT_PRECISION = 2  # 金额保留2位小数

    @classmethod
    def round_price(cls, value: Union[float, decimal.Decimal, str]) -> decimal.Decimal:
        """价格四舍五入，保留2位小数"""
        return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def round_ratio(cls, value: Union[float, decimal.Decimal, str]) -> decimal.Decimal:
        """比率四舍五入，保留4位小数"""
        return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.0001"), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def round_amount(cls, value: Union[float, decimal.Decimal, str]) -> decimal.Decimal:
        """金额四舍五入，保留2位小数"""
        return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def round_decimal(cls, value: Union[float, decimal.Decimal, str], precision: int = 4) -> decimal.Decimal:
        """通用小数四舍五入"""
        quantize_str = "0." + "0" * precision
        return decimal.Decimal(str(value)).quantize(decimal.Decimal(quantize_str), rounding=decimal.ROUND_HALF_UP)

    @classmethod
    def format_money(cls, amount: Union[float, decimal.Decimal, str]) -> str:
        """格式化金额，保留2位小数，千分位分隔"""
        amount_dec = cls.round_amount(amount)
        return f"{amount_dec:,.2f}"

    @classmethod
    def format_percent(cls, ratio: Union[float, decimal.Decimal, str]) -> str:
        """格式化百分比，保留2位小数"""
        ratio_dec = cls.round_ratio(ratio)
        return f"{ratio_dec * 100:,.2f}%"

    @classmethod
    def format_large_number(cls, number: Union[int, float]) -> str:
        """格式化大数字，简化显示"""
        if abs(number) >= 1e12:
            return f"{number/1e12:.2f}T"
        elif abs(number) >= 1e9:
            return f"{number/1e9:.2f}B"
        elif abs(number) >= 1e6:
            return f"{number/1e6:.2f}M"
        elif abs(number) >= 1e3:
            return f"{number/1e3:.2f}K"
        else:
            return f"{number:.2f}"

    @classmethod
    def is_equal(
        cls, a: Union[float, decimal.Decimal, str], b: Union[float, decimal.Decimal, str], precision: int = 4
    ) -> bool:
        """判断两个数值是否相等，指定精度"""
        precision_factor = decimal.Decimal(f"1e-{precision}")
        return abs(decimal.Decimal(str(a)) - decimal.Decimal(str(b))) < precision_factor

    @classmethod
    def calculate_fee(
        cls, amount: Union[float, decimal.Decimal], fee_rate: float, min_fee: float = 0.0
    ) -> decimal.Decimal:
        """计算手续费"""
        fee = cls.round_amount(decimal.Decimal(str(amount)) * decimal.Decimal(str(fee_rate)))
        return max(fee, cls.round_amount(min_fee))

    @classmethod
    def calculate_profit(
        cls,
        buy_price: Union[float, decimal.Decimal],
        sell_price: Union[float, decimal.Decimal],
        quantity: int,
        fee_rate: float = 0.0003,
        min_fee: float = 5.0,
        stamp_duty_rate: float = 0.001,
    ) -> decimal.Decimal:
        """计算交易利润（扣除手续费和印花税）"""
        buy_amount = cls.round_amount(decimal.Decimal(str(buy_price)) * quantity)
        sell_amount = cls.round_amount(decimal.Decimal(str(sell_price)) * quantity)

        # 买入手续费
        buy_fee = cls.calculate_fee(buy_amount, fee_rate, min_fee)
        # 卖出手续费 + 印花税（卖出时收）
        sell_fee = cls.calculate_fee(sell_amount, fee_rate, min_fee)
        stamp_duty = cls.calculate_fee(sell_amount, stamp_duty_rate)

        total_cost = buy_amount + buy_fee + sell_fee + stamp_duty
        profit = sell_amount - total_cost

        return cls.round_amount(profit)

    @classmethod
    def calculate_profit_ratio(
        cls, buy_price: Union[float, decimal.Decimal], sell_price: Union[float, decimal.Decimal], **kwargs
    ) -> decimal.Decimal:
        """计算利润率"""
        profit = cls.calculate_profit(buy_price, sell_price, **kwargs)
        buy_amount = cls.round_amount(decimal.Decimal(str(buy_price)) * kwargs.get("quantity", 1))
        if buy_amount == 0:
            return decimal.Decimal("0.0")
        return cls.round_ratio(profit / buy_amount)

    @classmethod
    def safe_divide(
        cls, numerator: Union[float, decimal.Decimal], denominator: Union[float, decimal.Decimal], default: float = 0.0
    ) -> decimal.Decimal:
        """安全除法，避免除零错误"""
        try:
            num = decimal.Decimal(str(numerator))
            den = decimal.Decimal(str(denominator))
            if den == 0:
                return decimal.Decimal(str(default))
            return num / den
        except (decimal.InvalidOperation, ZeroDivisionError):
            return decimal.Decimal(str(default))

    @classmethod
    def calculate_max_drawdown(cls, net_value_series: list) -> decimal.Decimal:
        """计算最大回撤"""
        if not net_value_series or len(net_value_series) < 2:
            return decimal.Decimal("0.0")

        peak = decimal.Decimal(str(net_value_series[0]))
        max_drawdown = decimal.Decimal("0.0")

        for value in net_value_series[1:]:
            current = decimal.Decimal(str(value))
            if current > peak:
                peak = current
            drawdown = (peak - current) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return cls.round_ratio(max_drawdown)

    @classmethod
    def calculate_sharpe_ratio(cls, returns: list, risk_free_rate: float = 0.03) -> decimal.Decimal:
        """计算夏普比率"""
        if not returns or len(returns) < 2:
            return decimal.Decimal("0.0")

        returns_arr = np.array(returns, dtype=np.float64)
        excess_returns = returns_arr - (risk_free_rate / 252)  # 日化无风险收益率

        if np.std(excess_returns) == 0:
            return decimal.Decimal("0.0")

        sharpe = np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
        return cls.round_ratio(sharpe)
