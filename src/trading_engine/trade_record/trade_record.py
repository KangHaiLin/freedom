"""
成交记录类
存储单次成交的详细信息
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any

from src.trading_engine.base.base_order import OrderSide


@dataclass
class TradeRecord:
    """
    成交记录
    存储单次成交的详细信息
    """
    trade_id: str
    order_id: str
    ts_code: str
    side: OrderSide
    filled_quantity: int
    filled_price: float
    filled_time: datetime
    strategy_id: Optional[str] = None
    commission: float = 0.0
    slippage: float = 0.0
    pnl: Optional[float] = None  # 本次交易实现盈亏（仅卖出时有值）
    position_before: int = 0
    position_after: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['side'] = self.side.name
        data['side_code'] = self.side.value
        data['filled_time'] = self.filled_time.isoformat()
        return data

    @property
    def turnover(self) -> float:
        """成交额 = 成交数量 * 成交价格"""
        return self.filled_quantity * self.filled_price

    @property
    def net_turnover(self) -> float:
        """净成交额 = 成交额 ± 佣金"""
        turn = self.turnover
        if self.side == OrderSide.BUY:
            return turn + self.commission  # 买入，佣金增加支出
        else:
            return turn - self.commission  # 卖出，佣金减少收入
        return turn

    @property
    def is_buy(self) -> bool:
        """是否是买入"""
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """是否是卖出"""
        return self.side == OrderSide.SELL

    def __repr__(self) -> str:
        return (
            f"TradeRecord(id={self.trade_id}, order_id={self.order_id}, "
            f"ts_code={self.ts_code}, side={self.side.name}, "
            f"qty={self.filled_quantity}, price={self.filled_price:.4f})"
        )
