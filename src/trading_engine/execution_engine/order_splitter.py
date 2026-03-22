"""
订单拆分器
将大单根据流动性和风险偏好拆分成多个小单
"""

import math
import random
from typing import List, Optional, Tuple

from src.trading_engine.base.base_order import OrderSide


class OrderSplitter:
    """
    订单拆分器
    提供多种拆分策略将大单拆分为小单，降低市场冲击
    """

    @staticmethod
    def split_equal(total_quantity: int, num_splits: int, min_chunk: int = 100) -> List[int]:
        """
        等份额拆分
        Args:
            total_quantity: 总数量
            num_splits: 拆分份数
            min_chunk: 最小单
        Returns:
            拆分后的数量列表
        """
        if num_splits <= 1:
            return [total_quantity]

        base = total_quantity // num_splits
        remainder = total_quantity % num_splits

        chunks = []
        for i in range(num_splits):
            chunk = base
            if i < remainder:
                chunk += 1
            if chunk >= min_chunk:
                chunks.append(chunk)
            elif chunk > 0:
                # 不够最小，加到最后一笔
                if chunks:
                    chunks[-1] += chunk
                else:
                    chunks.append(chunk)

        return chunks

    @staticmethod
    def split_vanilla(total_quantity: int, max_chunk: int, min_chunk: int = 100) -> List[int]:
        """
        简单受限拆分，不超过最大单笔
        Args:
            total_quantity: 总数量
            max_chunk: 最大单笔
            min_chunk: 最小单笔
        Returns:
            拆分后的数量列表
        """
        if total_quantity <= max_chunk:
            return [total_quantity]

        chunks = []
        remaining = total_quantity

        while remaining > 0:
            if remaining <= max_chunk:
                if remaining >= min_chunk:
                    chunks.append(remaining)
                else:
                    if chunks:
                        chunks[-1] += remaining
                    else:
                        chunks.append(remaining)
                break
            else:
                chunks.append(max_chunk)
                remaining -= max_chunk

        return chunks

    @staticmethod
    def split_random(
        total_quantity: int, num_splits: int, min_chunk: int = 100, max_chunk: int = 10000, seed: int = None
    ) -> List[int]:
        """
        随机拆分，减少可预测性
        Args:
            total_quantity: 总数量
            num_splits: 拆分份数
            min_chunk: 最小
            max_chunk: 最大
            seed: 随机种子
        Returns:
            拆分列表
        """
        if seed is not None:
            random.seed(seed)

        if num_splits <= 1:
            return [total_quantity]

        # 确保每笔至少min_chunk
        min_total = min_chunk * num_splits
        if min_total > total_quantity:
            # 减少份数
            num_splits = total_quantity // min_chunk
            if num_splits <= 0:
                return [total_quantity]
            min_total = min_chunk * num_splits

        remaining_after_min = total_quantity - min_total
        chunks = [min_chunk] * num_splits

        # 随机分配剩余
        for _ in range(remaining_after_min):
            idx = random.randint(0, num_splits - 1)
            if chunks[idx] < max_chunk:
                chunks[idx] += 1

        # 确保不超过max
        for i in range(num_splits):
            if chunks[i] > max_chunk:
                diff = chunks[i] - max_chunk
                chunks[i] = max_chunk
                # 分配diff给其他人
                while diff > 0:
                    idx = random.randint(0, num_splits - 1)
                    if chunks[idx] < max_chunk:
                        add = min(diff, max_chunk - chunks[idx])
                        chunks[idx] += add
                        diff -= add

        return [c for c in chunks if c > 0]

    @staticmethod
    def split_by_volume(
        total_quantity: int,
        market_volumes: List[int],
        participation_rate: float = 0.1,
        min_chunk: int = 100,
        max_chunk: int = 10000,
    ) -> List[int]:
        """
        根据市场成交量拆分，按比例参与
        Args:
            total_quantity: 总数量
            market_volumes: 每个时间段市场成交量
            participation_rate: 参与比例
            min_chunk: 最小单
            max_chunk: 最大单
        Returns:
            每个时间段的下单大小
        """
        total_market = sum(market_volumes)
        if total_market == 0:
            # 均分
            n = len(market_volumes)
            return OrderSplitter.split_equal(total_quantity, n, min_chunk)

        chunks = []
        remaining = total_quantity

        for vol in market_volumes:
            if remaining <= 0:
                break
            target = int(vol * participation_rate)
            target = max(min_chunk, min(max_chunk, target))
            target = min(target, remaining)
            if target > 0:
                chunks.append(target)
                remaining -= target

        # 如果还有剩余，均匀分配到前面
        if remaining > 0 and chunks:
            per_chunk = remaining // len(chunks)
            remainder = remaining % len(chunks)
            for i in range(len(chunks)):
                add = per_chunk + (1 if i < remainder else 0)
                new_size = min(chunks[i] + add, max_chunk)
                remaining -= new_size - chunks[i]
                chunks[i] = new_size
            if remaining > 0:
                chunks[-1] += remaining

        return chunks

    @staticmethod
    def calculate_optimal_splits(
        total_quantity: int,
        avg_daily_volume: float,
        participation_target: float = 0.1,
    ) -> int:
        """
        计算最优拆分份数，基于日均成交量
        Args:
            total_quantity: 订单总量
            avg_daily_volume: 日均成交量
            participation_target: 目标参与率
        Returns:
            建议拆分份数
        """
        if avg_daily_volume <= 0:
            return 1

        target_participation = total_quantity / avg_daily_volume
        if target_participation <= participation_target:
            return 1

        num_splits = math.ceil(target_participation / participation_target)
        return min(num_splits, 50)  # 最多50笔
