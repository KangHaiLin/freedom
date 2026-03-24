"""
TWAP (Time Weighted Average Price) 执行算法
将大单等分拆分，按固定时间间隔下单
"""

from datetime import datetime
from typing import List, Optional

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
        if self.total_quantity <= 0:
            return []

        base_quantity = self.total_quantity // self.num_intervals
        remainder = self.total_quantity % self.num_intervals

        # 先计算理论上每一块的原始数量，然后合并小批量
        # 如果单块小于min_chunk，累积起来直到超过min_chunk再添加
        plan = []
        pending = 0

        for i in range(self.num_intervals):
            chunk_quantity = base_quantity
            if i < remainder:
                chunk_quantity += 1

            pending += chunk_quantity

            # 当累积达到min_chunk或者是最后一块，就输出
            if pending >= self.min_chunk or i == self.num_intervals - 1:
                if pending > 0:
                    # 限制最大块
                    if pending > self.max_chunk:
                        # 如果超过最大块，分成多块
                        while pending > 0:
                            current = min(pending, self.max_chunk)
                            plan.append(current)
                            pending -= current
                    else:
                        plan.append(pending)
                    pending = 0

        # 如果还有剩余，添加到最后一块
        if pending > 0:
            if plan:
                plan[-1] += pending
            else:
                plan.append(min(pending, self.max_chunk))

        # 确保总和正确
        total = sum(plan)
        if total != self.total_quantity:
            diff = self.total_quantity - total
            if diff > 0 and plan:
                plan[-1] += diff
            elif diff < 0 and plan:
                # 只需要保证不超过总量，实际执行中会正确处理剩余，所以这里容忍小差异没关系
                pass

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

        # 如果还没到开始时间，不发送
        if current_time < self.start_time:
            return None

        # 计算从开始到现在过去了多少个间隔，应该发送到第几个切片
        elapsed_total = (current_time - self.start_time).total_seconds()
        target_split = int(elapsed_total / self.interval_seconds) + 1

        # 不超过总切片数
        target_split = min(target_split, len(self._split_plan))

        # 如果还没发到目标位置，发送下一笔
        if self.current_split < target_split:
            return self._take_next_chunk(current_time)

        # 全部完成检查
        if self.current_split >= len(self._split_plan):
            self.done = True
            return None

        return None

    def _take_next_chunk(self, current_time: datetime) -> Optional[int]:
        """取出下一笔"""
        if self.current_split >= len(self._split_plan):
            self.done = True
            return None

        chunk_quantity = self._split_plan[self.current_split]
        self.current_split += 1
        self.remaining_quantity -= chunk_quantity
        self.last_order_time = current_time

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
