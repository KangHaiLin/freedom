"""
回测结果和交易记录数据类
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any

from .enums import TradeDirection, PositionSide


@dataclass
class TradeRecord:
    """单笔交易记录"""
    trade_id: int
    ts_code: str
    direction: TradeDirection
    quantity: int
    price: float
    amount: float
    commission: float
    trade_date: datetime
    position_before: int
    position_after: int
    pnl: float = 0.0
    pnl_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['direction'] = self.direction.value
        return data


@dataclass
class PositionSnapshot:
    """持仓快照"""
    ts_code: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyStats:
    """每日统计"""
    date: Any
    total_assets: float
    cash: float
    market_value: float
    daily_pnl: float
    daily_pnl_pct: float
    turnover: float
    trades: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_pnl_pct: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_date: Optional[Any]
    win_rate: float
    profit_loss_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_holding_days: float
    turnover_rate: float  # 年均换手率
    daily_stats: list[DailyStats]
    trades: list[TradeRecord]
    positions: list[Dict[str, PositionSnapshot]]
    extra_info: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_name': self.strategy_name,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'annualized_return': self.annualized_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_holding_days': self.avg_holding_days,
            'turnover_rate': self.turnover_rate,
            'extra_info': self.extra_info,
        }
