"""
风险限额管理器
支持多维度风险限额管理：用户级别、单票级别、每日累计等
"""
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from collections import defaultdict


class LimitType:
    """限额类型常量"""
    USER_DAILY_AMOUNT = "user_daily_amount"    # 用户单日累计交易金额
    USER_TOTAL_AMOUNT = "user_total_amount"    # 用户总交易金额
    SINGLE_POSITION_RATIO = "single_position_ratio"  # 单票持仓比例
    MAX_POSITIONS_COUNT = "max_positions_count"  # 最大持仓数量
    DAILY_ORDER_COUNT = "daily_order_count"  # 单日订单数量
    LEVERAGE = "leverage"  # 杠杆限额


class RiskLimit:
    """风险限额定义"""

    def __init__(
        self,
        limit_id: int,
        limit_type: str,
        limit_value: float,
        user_id: Optional[int] = None,
        ts_code: Optional[str] = None,
        enabled: bool = True,
        description: Optional[str] = None,
    ):
        self.limit_id = limit_id
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.user_id = user_id
        self.ts_code = ts_code
        self.enabled = enabled
        self.description = description
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def match(self, user_id: Optional[int], ts_code: Optional[str]) -> bool:
        """检查此限额是否匹配该条件"""
        if self.user_id is not None and user_id != self.user_id:
            return False
        if self.ts_code is not None and ts_code != self.ts_code:
            return False
        return self.enabled

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            'limit_id': self.limit_id,
            'limit_type': self.limit_type,
            'limit_value': self.limit_value,
            'user_id': self.user_id,
            'ts_code': self.ts_code,
            'enabled': self.enabled,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class LimitManager:
    """
    风险限额管理器
    管理各类风险限额，提供限额检查功能
    """

    def __init__(self):
        self._limits: Dict[int, RiskLimit] = {}
        self._next_id = 1
        # 按类型分组缓存
        self._limits_by_type: Dict[str, List[int]] = defaultdict(list)
        # 今日已用额度统计
        self._daily_usage: Dict[Tuple[Optional[int], str], float] = defaultdict(float)

    def add_limit(self, limit: RiskLimit) -> int:
        """添加限额，返回限额ID"""
        limit_id = self._next_id
        self._next_id += 1
        limit.limit_id = limit_id
        self._limits[limit_id] = limit
        self._limits_by_type[limit.limit_type].append(limit_id)
        return limit_id

    def remove_limit(self, limit_id: int) -> bool:
        """删除限额"""
        if limit_id not in self._limits:
            return False
        limit = self._limits[limit_id]
        self._limits_by_type[limit.limit_type].remove(limit_id)
        del self._limits[limit_id]
        return True

    def enable_limit(self, limit_id: int) -> bool:
        """启用限额"""
        if limit_id in self._limits:
            self._limits[limit_id].enabled = True
            return True
        return False

    def disable_limit(self, limit_id: int) -> bool:
        """禁用限额"""
        if limit_id in self._limits:
            self._limits[limit_id].enabled = False
            return True
        return False

    def get_limit(self, limit_id: int) -> Optional[RiskLimit]:
        """获取限额"""
        return self._limits.get(limit_id)

    def get_limits_by_type(self, limit_type: str) -> List[RiskLimit]:
        """获取某类型所有限额"""
        ids = self._limits_by_type.get(limit_type, [])
        return [self._limits[i] for i in ids if self._limits[i].enabled]

    def get_all_limits(self) -> List[RiskLimit]:
        """获取所有限额"""
        return list(self._limits.values())

    def check_limit(
        self,
        limit_type: str,
        current_value: float,
        user_id: Optional[int] = None,
        ts_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        检查是否超过限额

        Args:
            limit_type: 限额类型
            current_value: 当前值
            user_id: 用户ID
            ts_code: 股票代码

        Returns:
            检查结果
        """
        # 查找匹配的限额
        matching_limits = []
        for limit in self.get_limits_by_type(limit_type):
            if limit.match(user_id, ts_code):
                matching_limits.append(limit)

        if not matching_limits:
            # 没有匹配限额，默认通过
            return {
                'passed': True,
                'message': '无匹配限额',
                'current_value': current_value,
            }

        # 找出最严格的（最小的）限额
        most_strict = min(matching_limits, key=lambda l: l.limit_value)

        if current_value > most_strict.limit_value:
            return {
                'passed': False,
                'message': f'超出{limit_type}限额: 当前{current_value:.2f}, 限额{most_strict.limit_value:.2f}',
                'current_value': current_value,
                'limit_value': most_strict.limit_value,
                'limit_id': most_strict.limit_id,
            }

        return {
            'passed': True,
            'message': '检查通过',
            'current_value': current_value,
            'limit_value': most_strict.limit_value,
        }

    def check_daily_amount(
        self,
        user_id: int,
        additional_amount: float,
        limit: float,
    ) -> Dict[str, Any]:
        """
        检查单日交易金额限额

        Args:
            user_id: 用户ID
            additional_amount: 本次新增金额
            limit: 限额

        Returns:
            检查结果
        """
        key = (user_id, LimitType.USER_DAILY_AMOUNT)
        current_total = self._daily_usage[key] + additional_amount

        result = self.check_limit(
            LimitType.USER_DAILY_AMOUNT,
            current_total,
            user_id=user_id,
        )

        if result['passed']:
            # 更新已用额度
            self._daily_usage[key] = current_total

        return result

    def record_usage(
        self,
        limit_type: str,
        amount: float,
        user_id: Optional[int] = None,
    ) -> None:
        """记录使用额度"""
        key = (user_id, limit_type)
        self._daily_usage[key] += amount

    def reset_daily_usage(self, date: Optional[date] = None) -> None:
        """重置每日额度使用统计（每日开盘调用）"""
        self._daily_usage.clear()

    def get_daily_usage(
        self,
        limit_type: str,
        user_id: Optional[int] = None,
    ) -> float:
        """获取今日已用额度"""
        key = (user_id, limit_type)
        return self._daily_usage.get(key, 0.0)

    def get_daily_usage_summary(self) -> Dict[str, Any]:
        """获取今日使用统计"""
        result = {}
        for (user_id, limit_type), used in self._daily_usage.items():
            key = f"{user_id or 'global'}_{limit_type}"
            result[key] = used
        return result

    def set_default_limits(
        self,
        max_single_position_ratio: float = 0.3,
        max_positions_count: int = 20,
        user_daily_amount: float = 1000000,
        daily_order_count: int = 50,
    ) -> None:
        """设置默认限额"""
        # 默认单票持仓比例
        self.add_limit(RiskLimit(
            limit_id=0,
            limit_type=LimitType.SINGLE_POSITION_RATIO,
            limit_value=max_single_position_ratio,
            description='默认单票持仓比例限额',
        ))
        # 默认最大持仓数量
        self.add_limit(RiskLimit(
            limit_id=0,
            limit_type=LimitType.MAX_POSITIONS_COUNT,
            limit_value=max_positions_count,
            description='默认最大持仓数量限额',
        ))
        # 默认用户单日金额
        self.add_limit(RiskLimit(
            limit_id=0,
            limit_type=LimitType.USER_DAILY_AMOUNT,
            limit_value=user_daily_amount,
            description='默认用户单日交易金额限额',
        ))
        # 默认每日订单数量
        self.add_limit(RiskLimit(
            limit_id=0,
            limit_type=LimitType.DAILY_ORDER_COUNT,
            limit_value=daily_order_count,
            description='默认每日订单数量限额',
        ))

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'ok',
            'total_limits': len(self._limits),
            'enabled_limits': sum(1 for l in self._limits.values() if l.enabled),
            'daily_usage_entries': len(self._daily_usage),
            'by_type': {t: len(ids) for t, ids in self._limits_by_type.items()},
        }
