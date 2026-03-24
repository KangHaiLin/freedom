"""
订单管理器
管理所有订单，提供查询、新增、取消等功能
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.trading_engine.base.base_order import BaseOrder, OrderStatus
from src.trading_engine.order_management.order_state_machine import OrderStateMachine

logger = logging.getLogger(__name__)


class OrderManager:
    """订单管理器，统一管理所有订单生命周期"""

    def __init__(self):
        """初始化订单管理器"""
        self._orders: Dict[str, BaseOrder] = {}
        self._state_machine = OrderStateMachine()

    def add_order(self, order: BaseOrder) -> str:
        """
        添加订单
        Args:
            order: 订单对象
        Returns:
            订单ID
        """
        if not order.order_id:
            logger.warning("订单缺少order_id")
            return ""
        if order.order_id in self._orders:
            logger.warning(f"订单ID重复: {order.order_id}")
            return order.order_id
        self._orders[order.order_id] = order
        logger.debug(f"添加订单: {order.order_id}, {order.ts_code}")
        return order.order_id

    def get_order(self, order_id: str) -> Optional[BaseOrder]:
        """
        获取订单
        Args:
            order_id: 订单ID
        Returns:
            订单对象，不存在返回None
        """
        return self._orders.get(order_id)

    def remove_order(self, order_id: str) -> bool:
        """
        移除订单
        Args:
            order_id: 订单ID
        Returns:
            是否移除成功
        """
        if order_id in self._orders:
            del self._orders[order_id]
            logger.debug(f"移除订单: {order_id}")
            return True
        return False

    def update_order_status(self, order_id: str, new_status: OrderStatus) -> Tuple[bool, Optional[str]]:
        """
        更新订单状态
        Args:
            order_id: 订单ID
            new_status: 新状态
        Returns:
            (是否成功, 错误信息)
        """
        order = self.get_order(order_id)
        if order is None:
            return False, f"订单不存在: {order_id}"

        if not self._state_machine.can_transition(order.status, new_status):
            error_msg = self._state_machine.validate_transition(order.status, new_status)
            logger.warning(error_msg)
            return False, error_msg

        success = self._state_machine.transition(order, new_status)
        if success:
            logger.debug(f"订单状态更新: {order_id} {order.status.name} → {new_status.name}")
        return success, None if success else "状态转换失败"

    def submit_order(self, order: BaseOrder) -> str:
        """
        提交订单（新增并更新状态）
        Args:
            order: 订单对象
        Returns:
            订单ID
        """
        order_id = self.add_order(order)
        if not order_id:
            return ""
        order.submit()
        return order_id

    def cancel_order(self, order_id: str) -> Tuple[bool, Optional[str]]:
        """
        取消订单
        Args:
            order_id: 订单ID
        Returns:
            (是否成功, 错误信息)
        """
        order = self.get_order(order_id)
        if order is None:
            return False, f"订单不存在: {order_id}"
        if not order.can_cancel():
            return False, f"订单当前状态 {order.status.name} 不可取消"
        order.cancel()
        logger.info(f"订单已取消: {order_id}")
        return True, None

    def fill_order(
        self, order_id: str, filled_quantity: int, filled_price: float, filled_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        成交处理
        Args:
            order_id: 订单ID
            filled_quantity: 成交数量
            filled_price: 成交价格
            filled_time: 成交时间
        Returns:
            (是否成功, 错误信息)
        """
        order = self.get_order(order_id)
        if order is None:
            return False, f"订单不存在: {order_id}"

        if filled_quantity <= 0:
            return False, "成交数量必须大于0"

        remaining = order.get_remaining_quantity()
        if filled_quantity > remaining:
            return False, f"成交数量超过剩余数量: {filled_quantity} > {remaining}"

        order.fill(filled_quantity, filled_price, filled_time)
        logger.info(
            f"订单成交: {order_id}, 成交数量: {filled_quantity}, "
            f"成交价格: {filled_price:.4f}, 已成交: {order.filled_quantity}/{order.quantity}"
        )
        return True, None

    def reject_order(self, order_id: str, reason: str = "") -> Tuple[bool, Optional[str]]:
        """
        拒绝订单
        Args:
            order_id: 订单ID
            reason: 拒绝原因
        Returns:
            (是否成功, 错误信息)
        """
        order = self.get_order(order_id)
        if order is None:
            return False, f"订单不存在: {order_id}"
        order.reject()
        if reason:
            order.extra_info["reject_reason"] = reason
        logger.info(f"订单被拒绝: {order_id}, 原因: {reason}")
        return True, None

    def query_orders(
        self,
        status: Optional[List[OrderStatus]] = None,
        ts_code: Optional[str] = None,
        strategy_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        side: Optional[int] = None,
    ) -> List[BaseOrder]:
        """
        查询订单，支持多条件过滤
        Args:
            status: 状态过滤
            ts_code: 股票代码过滤
            strategy_id: 策略ID过滤
            start_time: 创建时间起始过滤
            end_time: 创建时间结束过滤
            side: 买卖方向过滤
        Returns:
            符合条件的订单列表
        """
        result = []
        for order in self._orders.values():
            # 状态过滤
            if status is not None and order.status not in status:
                continue
            # 股票代码过滤
            if ts_code is not None and order.ts_code != ts_code:
                continue
            # 策略ID过滤
            if strategy_id is not None and order.strategy_id != strategy_id:
                continue
            # 买卖方向过滤
            if side is not None and order.side.value != side:
                continue
            # 时间过滤
            if start_time is not None and order.created_at < start_time:
                continue
            if end_time is not None and order.created_at > end_time:
                continue
            result.append(order)
        return result

    def get_active_orders(self, ts_code: Optional[str] = None) -> List[BaseOrder]:
        """
        获取所有活跃订单（可成交或取消）
        Args:
            ts_code: 指定股票代码，None表示返回所有
        Returns:
            活跃订单列表
        """
        active_status = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL,
        ]
        return self.query_orders(status=active_status, ts_code=ts_code)

    def get_order_count(self) -> int:
        """获取订单总数"""
        return len(self._orders)

    def get_statistics(self) -> Dict[str, int]:
        """获取订单统计信息"""
        stats = {status.name: 0 for status in OrderStatus}
        for order in self._orders.values():
            stats[order.status.name] += 1
        stats["total"] = len(self._orders)
        stats["active"] = len(self.get_active_orders())
        return stats

    def clear_all(self) -> None:
        """清空所有订单"""
        self._orders.clear()
        logger.debug("清空所有订单")

    def get_all_orders(self) -> List[BaseOrder]:
        """获取所有订单"""
        return list(self._orders.values())

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_statistics()
        return {
            "status": "ok",
            "total_orders": stats["total"],
            "active_orders": stats["active"],
        }
