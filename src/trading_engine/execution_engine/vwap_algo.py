"""
VWAP (Volume Weighted Average Price) 执行算法
将大单拆分成多个小订单，在一段时间内均匀成交，减少市场冲击
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np

from src.trading_engine.base.base_order import OrderSide


class VWAPAlgo:
    """
    VWAP 执行算法
    目标：使成交均价接近市场成交量加权平均价格
    """

    def __init__(
        self,
        total_quantity: int,
        side: OrderSide,
        start_time: datetime,
        end_time: datetime,
        min_chunk: int = 100,  # 最小下单单位（股）
        max_chunk: int = 10000,  # 最大下单单位（股）
        num_splits: Optional[int] = None,
    ):
        """
        初始化VWAP执行
        Args:
            total_quantity: 总成交量
            side: 买卖方向
            start_time: 开始时间
            end_time: 结束时间
            min_chunk: 最小单笔数量
            max_chunk: 最大单笔数量
            num_splits: 拆分份数，如果为None则自动计算
        """
        self.total_quantity = total_quantity
        self.side = side
        self.start_time = start_time
        self.end_time = end_time
        self.min_chunk = min_chunk
        self.max_chunk = max_chunk

        self.remaining_quantity = total_quantity
        self.done = False

        # 自动计算拆分份数
        if num_splits is None:
            # 按每1000股一份，最少5份，最多50份
            num_splits = max(5, min(50, total_quantity // min_chunk))
        self.num_splits = num_splits

        # 计算时间区间
        self.total_duration = (end_time - start_time).total_seconds()
        self.interval = self.total_duration / num_splits if num_splits > 0 else 0

        self.current_split = 0
        self._split_plan = self._create_split_plan()

    def _create_split_plan(self) -> List[Tuple[datetime, int]]:
        """创建拆分计划"""
        plan = []
        remaining = self.total_quantity

        # 平均分配
        base_quantity = self.total_quantity // self.num_splits
        remainder = self.total_quantity % self.num_splits

        for i in range(self.num_splits):
            chunk_quantity = base_quantity
            if i < remainder:
                chunk_quantity += 1

            # 限制在min-max范围内
            chunk_quantity = max(self.min_chunk, min(self.max_chunk, chunk_quantity))

            # 计算成交时间
            offset_seconds = self.interval * (i + 0.5)  # 中间时间
            chunk_time = self.start_time + timedelta(seconds=offset_seconds)
            plan.append((chunk_time, chunk_quantity))
            remaining -= chunk_quantity

        # 如果还有剩余，分配到最后一笔
        if remaining > 0:
            last_time, last_qty = plan[-1]
            plan[-1] = (last_time, last_qty + remaining)

        return plan

    def get_next_order(self, current_time: datetime) -> Optional[int]:
        """
        获取下一笔应该下单的数量
        Args:
            current_time: 当前时间
        Returns:
            如果到了执行时间，返回需要下单的数量，否则返回None
        """
        if self.done:
            return None

        while self.current_split < len(self._split_plan):
            chunk_time, chunk_quantity = self._split_plan[self.current_split]
            if current_time >= chunk_time:
                # 可以执行这一笔
                self.current_split += 1
                self.remaining_quantity -= chunk_quantity
                if self.current_split >= len(self._split_plan):
                    self.done = True
                return chunk_quantity
            else:
                # 还没到时间
                return None

        self.done = True
        return None

    def get_remaining_quantity(self) -> int:
        """获取剩余数量"""
        return self.remaining_quantity

    def is_done(self) -> bool:
        """是否完成"""
        return self.done or self.remaining_quantity <= 0

    def get_progress(self) -> float:
        """获取执行进度 (0-1)"""
        if self.total_quantity == 0:
            return 1.0
        return 1.0 - self.remaining_quantity / self.total_quantity

    def get_split_plan(self) -> List[Tuple[datetime, int]]:
        """获取完整拆分计划"""
        return self._split_plan.copy()


class ParticipationVWAP(VWAPAlgo):
    """
    参与型VWAP
    根据市场成交量比例参与成交，更灵活的冲击控制
    """

    def __init__(
        self,
        total_quantity: int,
        side: OrderSide,
        start_time: datetime,
        end_time: datetime,
        participation_rate: float = 0.1,  # 目标参与市场成交量的比例
        min_chunk: int = 100,
        max_chunk: int = 10000,
    ):
        """
        初始化参与型VWAP
        Args:
            participation_rate: 参与市场成交量比例，一般0.1-0.3（10%-30%）
        """
        # 先按平均拆分初始化
        super().__init__(total_quantity, side, start_time, end_time, min_chunk, max_chunk)
        self.participation_rate = participation_rate
        self.last_volume = 0

    def adjust_next_chunk(self, market_volume: float) -> int:
        """
        根据当前市场成交量调整下一笔大小
        Args:
            market_volume: 当前时间段市场成交量
        Returns:
            下一笔订单大小
        """
        if self.is_done():
            return 0
        target_chunk = int(market_volume * self.participation_rate)
        target_chunk = max(self.min_chunk, min(self.max_chunk, target_chunk))
        target_chunk = min(target_chunk, self.remaining_quantity)
        self.remaining_quantity -= target_chunk
        if self.remaining_quantity <= 0:
            self.done = True
        return target_chunk
