"""
券商接口定义
定义通用的佣金计算规则和接口常量
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommissionConfig:
    """佣金配置"""

    # 佣金费率，一般万3
    commission_rate: float = 0.0003
    # 最低佣金
    min_commission: float = 5.0
    # 印花税（卖出时收取，千分之一）
    stamp_duty_rate: float = 0.001
    # 过户费（双向收取，万分之0.2）
    transfer_fee_rate: float = 0.00002


class BrokerInterface:
    """券商接口常量定义"""

    # 交易时间
    OPEN_MORNING_START = "09:30:00"
    OPEN_MORNING_END = "11:30:00"
    OPEN_AFTERNOON_START = "13:00:00"
    OPEN_AFTERNOON_END = "15:00:00"

    # 涨跌停限制
    DEFAULT_PRICE_LIMIT = 0.10  # 10%
    ST_PRICE_LIMIT = 0.05  # 5%
    STAR_ST_PRICE_LIMIT = 0.20  # 20%

    # T+1 规则
    # 当日买入股票，下一交易日才能卖出


class CommissionCalculator:
    """佣金计算器，按照A股标准计算手续费"""

    def __init__(self, config: Optional[CommissionConfig] = None):
        self.config = config or CommissionConfig()

    def calculate_commission(self, quantity: int, price: float, is_buy: bool) -> float:
        """
        计算总手续费（佣金+印花税+过户费）
        Args:
            quantity: 成交数量
            price: 成交价格
            is_buy: 是否买入
        Returns:
            总手续费
        """
        turnover = quantity * price

        # 佣金
        commission = turnover * self.config.commission_rate
        if commission < self.config.min_commission:
            commission = self.config.min_commission

        # 印花税 - 仅卖出收取
        stamp_duty = turnover * self.config.stamp_duty_rate if not is_buy else 0.0

        # 过户费 - 双向收取
        transfer_fee = turnover * self.config.transfer_fee_rate

        total = commission + stamp_duty + transfer_fee
        return total

    def calculate_buy_commission(self, quantity: int, price: float) -> float:
        """计算买入手续费"""
        return self.calculate_commission(quantity, price, is_buy=True)

    def calculate_sell_commission(self, quantity: int, price: float) -> float:
        """计算卖出手续费"""
        return self.calculate_commission(quantity, price, is_buy=False)
