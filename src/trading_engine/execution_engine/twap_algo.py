"""
TWAP (Time Weighted Average Price) 执行算法
将大单等分拆分，按固定时间间隔下单
"""
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

from src.trading_engine.base.base_order import OrderSide


class TWAPAlgo:
    """
    TWAP 执行算法
    将大单平均拆分，按固定时间间隔均匀下单
    """

    def __init__(
        self,
        total_quantity: int,
        side: OrderSide,
        start_time: datetime,
        end_time: datetime,
        interval_seconds: float = 300,  # 5分钟间隔
        min_chunk: int = 100,
        max_chunk: int = 10000,
    ):
        """
        初始化TWAP执行
        Args:
            total_quantity: 总成交量
            side: 买卖方向
            start_time: 开始时间
            end_time: 结束时间
            interval_seconds: 下单间隔秒数
            min_chunk: 最小单笔数量
            max_chunk: 最大单笔数量
        """
        self.total_quantity = total_quantity
        self.side = side
        self.start_time = start_time
        self.end_time = end_time
        self.interval_seconds = interval_seconds
        self.min_chunk = min_chunk
        self.max_chunk = max_chunk

        self.remaining_quantity = total_quantity
        self.done = False
        self.last_order_time: Optional[datetime] = None

        # 计算拆分数量
        total_duration = (end_time - start_time).total_seconds()
        self.num_intervals = max(1, int(total_duration / interval_seconds))
        self._split_plan = self._create_split_plan()
        self.current_split = 0

    def _create_split_plan(self) -> List[int]:
        """创建拆分计划"""
        plan = []
        remaining = self.total_quantity

        base_quantity = self.total_quantity // self.num_intervals
        remainder = self.total_quantity % self.num_intervals

        for i in range(self.num_intervals):
            chunk_quantity = base_quantity
            if i < remainder:
                chunk_quantity += 1

            # 限制范围
            if chunk_quantity > 0:
                chunk_quantity = max(self.min_chunk, min(self.max_chunk, chunk_quantity))

            if chunk_quantity > 0:
                plan.append(chunk_quantity)
                remaining -= chunk_quantity

        # 分配剩余
        if remaining > 0 and plan:
            plan[-1] += remaining

        # 如果总量太小，合并成一笔
        if not plan and remaining > 0:
            plan.append(min(remaining, self.max_chunk))

        return plan

    def get_next_order(self, current_time: datetime) -> Optional[int]:
        """
        获取下一笔订单
        Args:
            current_time: 当前时间
        Returns:
            下一单数量，如果没到时间或已完成返回None
        """
        if self.done:
            return None

        if self.last_order_time is None:
            # 第一笔，如果已经过了开始时间，立即执行
            if current_time >= self.start_time:
                return self._take_next_chunk()
            return None

        # 检查间隔
        elapsed = (current_time - self.last_order_time).total_seconds()
        if elapsed >= self.interval_seconds:
            return self._take_next_chunk()

        return None

    def _take_next_chunk(self) -> Optional[int]:
        """取出下一笔"""
        if self.current_split >= len(self._split_plan):
            self.done = True
            return None

        chunk_quantity = self._split_plan[self.current_split]
        self.current_split += 1
        self.remaining_quantity -= chunk_quantity
        self.last_order_time = datetime.now()

        if self.current_split >= len(self._split_plan):
            self.done = True

        return chunk_quantity

    def get_remaining_quantity(self) -> int:
        """获取剩余数量"""
        return self.remaining_quantity

    def is_done(self) -> bool:
        """是否完成"""
        return self.done or self.remaining_quantity <= 0

    def get_progress(self) -> float:
        """获取进度"""
        if self.total_quantity == 0:
            return 1.0
        return 1.0 - self.remaining_quantity / self.total_quantity

    def get_split_plan(self) -> List[int]:
        """获取拆分计划"""
        return self._split_plan.copy()
