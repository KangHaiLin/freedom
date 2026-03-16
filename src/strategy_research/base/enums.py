"""
策略研究枚举定义
"""
from enum import Enum


class StrategyStatus(Enum):
    """策略状态"""
    DRAFT = "draft"          # 草稿
    BACKTESTING = "backtesting"  # 回测中
    READY = "ready"          # 就绪可用
    RUNNING = "running"      # 实盘运行中
    PAUSED = "paused"        # 暂停
    DISABLED = "disabled"    # 已禁用
    DEPRECATED = "deprecated"  # 已废弃


class TradeDirection(Enum):
    """交易方向"""
    BUY = "BUY"        # 买入
    SELL = "SELL"      # 卖出
    HOLD = "HOLD"      # 持有


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"      # 多头
    SHORT = "short"    # 空头（A股目前不支持，但预留）


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"      # 市价单
    LIMIT = "limit"        # 限价单
    STOP_LOSS = "stop_loss"  # 止损单
    TAKE_PROFIT = "take_profit"  # 止盈单
