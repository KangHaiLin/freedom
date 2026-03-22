"""
模拟交易配置
"""

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """模拟交易配置"""

    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003  # 佣金率万分之三
    min_commission: float = 5.0  # 最低佣金
    slippage: float = 0.001  # 滑点0.1%
    enable_short: bool = False  # 不支持做空
