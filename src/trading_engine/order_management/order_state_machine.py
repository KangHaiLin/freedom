"""
订单状态机
管理订单状态转换，验证状态转换合法性
"""

from typing import Dict, Optional, Set

from src.trading_engine.base.base_order import BaseOrder, OrderStatus


class OrderStateMachine:
    """订单状态机，管理订单状态转换规则"""

    # 定义合法的状态转移图
    # key: 当前状态, value: 可以转移到的目标状态集合
    TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
        OrderStatus.PENDING: {
            OrderStatus.SUBMITTED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        },
        OrderStatus.SUBMITTED: {
            OrderStatus.PARTIAL,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        },
        OrderStatus.PARTIAL: {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        },
        OrderStatus.FILLED: set(),  # 终态
        OrderStatus.CANCELLED: set(),  # 终态
        OrderStatus.REJECTED: set(),  # 终态
        OrderStatus.EXPIRED: set(),  # 终态
    }

    @classmethod
    def can_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> bool:
        """
        检查状态转换是否合法
        Args:
            from_status: 当前状态
            to_status: 目标状态
        Returns:
            是否可以转换
        """
        if from_status == to_status:
            return True  # 允许保持原状
        if from_status not in cls.TRANSITIONS:
            return False
        return to_status in cls.TRANSITIONS[from_status]

    @classmethod
    def transition(cls, order: BaseOrder, to_status: OrderStatus) -> bool:
        """
        执行状态转换
        Args:
            order: 订单对象
            to_status: 目标状态
        Returns:
            是否转换成功
        """
        if not cls.can_transition(order.status, to_status):
            return False
        order.update_status(to_status)
        return True

    @classmethod
    def is_terminal(cls, status: OrderStatus) -> bool:
        """
        检查是否是终态（不再接受任何状态转移）
        Args:
            status: 状态
        Returns:
            是否是终态
        """
        return len(cls.TRANSITIONS.get(status, set())) == 0

    @classmethod
    def is_active(cls, status: OrderStatus) -> bool:
        """
        检查订单是否处于活跃状态（仍可成交或取消）
        Args:
            status: 状态
        Returns:
            是否活跃
        """
        active_states = {
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL,
        }
        return status in active_states

    @classmethod
    def get_available_transitions(cls, current_status: OrderStatus) -> Set[OrderStatus]:
        """
        获取当前状态所有可用的目标状态
        Args:
            current_status: 当前状态
        Returns:
            可用目标状态集合
        """
        return cls.TRANSITIONS.get(current_status, set())

    @classmethod
    def validate_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> Optional[str]:
        """
        验证状态转换，返回错误信息如果不合法
        Args:
            from_status: 当前状态
            to_status: 目标状态
        Returns:
            错误信息，合法返回None
        """
        if not cls.can_transition(from_status, to_status):
            return (
                f"无效状态转换: {from_status.name} → {to_status.name}, "
                f"合法目标状态: {[s.name for s in cls.get_available_transitions(from_status)]}"
            )
        return None
