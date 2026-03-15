"""
成交记录管理器
管理所有成交记录，提供查询和统计
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from src.trading_engine.trade_record.trade_record import TradeRecord
from src.trading_engine.order_management.order import Order
from src.trading_engine.base.base_order import OrderSide, OrderStatus
from src.trading_engine.position_management.position import Position

logger = logging.getLogger(__name__)


class TradeRecordManager:
    """成交记录管理器，统一管理所有成交记录"""

    def __init__(self):
        """初始化"""
        self._records: Dict[str, TradeRecord] = {}
        self._order_trades: Dict[str, List[str]] = {}  # order_id -> list[trade_id]

    def _generate_trade_id(self) -> str:
        """生成唯一成交ID"""
        return str(uuid.uuid4())[:8]

    def add_record(
        self,
        order: Order,
        filled_quantity: int,
        filled_price: float,
        filled_time: datetime,
        commission: float = 0.0,
        slippage: float = 0.0,
        pnl: Optional[float] = None,
        position_before: int = 0,
        position_after: int = 0,
    ) -> TradeRecord:
        """
        添加成交记录
        Args:
            order: 订单
            filled_quantity: 成交数量
            filled_price: 成交价格
            filled_time: 成交时间
            commission: 佣金
            slippage: 滑点
            pnl: 实现盈亏（卖出时）
            position_before: 成交前持仓
            position_after: 成交后持仓
        Returns:
            新建的成交记录
        """
        trade_id = self._generate_trade_id()
        record = TradeRecord(
            trade_id=trade_id,
            order_id=order.order_id,
            ts_code=order.ts_code,
            side=order.side,
            filled_quantity=filled_quantity,
            filled_price=filled_price,
            filled_time=filled_time,
            strategy_id=order.strategy_id,
            commission=commission,
            slippage=slippage,
            pnl=pnl,
            position_before=position_before,
            position_after=position_after,
        )
        self._records[trade_id] = record
        if order.order_id not in self._order_trades:
            self._order_trades[order.order_id] = []
        self._order_trades[order.order_id].append(trade_id)
        logger.debug(
            f"添加成交记录: {trade_id}, order: {order.order_id}, "
            f"{order.ts_code} {order.side.name} {filled_quantity} @ {filled_price}"
        )
        return record

    def get_record(self, trade_id: str) -> Optional[TradeRecord]:
        """
        获取成交记录
        Args:
            trade_id: 成交ID
        Returns:
            成交记录，不存在返回None
        """
        return self._records.get(trade_id)

    def get_trades_by_order(self, order_id: str) -> List[TradeRecord]:
        """
        获取订单的所有成交记录
        Args:
            order_id: 订单ID
        Returns:
            成交记录列表
        """
        trade_ids = self._order_trades.get(order_id, [])
        return [self._records[tid] for tid in trade_ids if tid in self._records]

    def query_records(
        self,
        ts_code: Optional[str] = None,
        strategy_id: Optional[str] = None,
        side: Optional[OrderSide] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TradeRecord]:
        """
        查询成交记录，多条件过滤
        Args:
            ts_code: 股票代码过滤
            strategy_id: 策略ID过滤
            side: 买卖方向过滤
            start_time: 开始时间
            end_time: 结束时间
        Returns:
            符合条件的成交记录列表
        """
        result = []
        for record in self._records.values():
            if ts_code is not None and record.ts_code != ts_code:
                continue
            if strategy_id is not None and record.strategy_id != strategy_id:
                continue
            if side is not None and record.side != side:
                continue
            if start_time is not None and record.filled_time < start_time:
                continue
            if end_time is not None and record.filled_time > end_time:
                continue
            result.append(record)
        # 按成交时间排序
        result.sort(key=lambda r: r.filled_time)
        return result

    def get_all_records(self) -> List[TradeRecord]:
        """获取所有成交记录，按时间排序"""
        records = list(self._records.values())
        records.sort(key=lambda r: r.filled_time)
        return records

    def get_trade_count(self) -> int:
        """获取成交总条数"""
        return len(self._records)

    def get_total_turnover(self) -> float:
        """获取总成交额"""
        return sum(r.turnover for r in self._records.values())

    def get_total_commission(self) -> float:
        """获取总佣金"""
        return sum(r.commission for r in self._records.values())

    def get_realized_pnl_total(self) -> float:
        """获取总实现盈亏"""
        total = 0.0
        for record in self._records.values():
            if record.pnl is not None:
                total += record.pnl
        return total

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        buys = [r for r in self._records.values() if r.is_buy]
        sells = [r for r in self._records.values() if r.is_sell]
        return {
            'total_trades': self.get_trade_count(),
            'buy_trades': len(buys),
            'sell_trades': len(sells),
            'total_turnover': self.get_total_turnover(),
            'buy_turnover': sum(r.turnover for r in buys),
            'sell_turnover': sum(r.turnover for r in sells),
            'total_commission': self.get_total_commission(),
            'total_realized_pnl': self.get_realized_pnl_total(),
        }

    def to_list_dict(self) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [r.to_dict() for r in self.get_all_records()]

    def clear_all(self) -> None:
        """清空所有记录"""
        self._records.clear()
        self._order_trades.clear()
        logger.debug("清空所有成交记录")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_statistics()
        return {
            'status': 'ok',
            'total_trades': stats['total_trades'],
            'total_turnover': stats['total_turnover'],
            'total_commission': stats['total_commission'],
        }
