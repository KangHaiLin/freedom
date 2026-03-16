"""
回测配置
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1000000.0  # 初始资金
    start_date: any = None  # 开始日期
    end_date: any = None  # 结束日期
    commission_rate: float = 0.0003  # 佣金率万分之三
    min_commission: float = 5.0  # 最低佣金5元
    slippage: float = 0.001  # 滑点 0.1%
    enable_short: bool = False  # 是否允许做空（A股不支持）
    close_at_end: bool = True  # 回测结束是否平仓所有持仓
    max_position_count: Optional[int] = None  # 最大持仓数量限制
    single_position_max_ratio: Optional[float] = None  # 单票最大比例限制
