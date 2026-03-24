"""
模拟券商适配器
用于回测和模拟交易，提供撮合成交功能
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.trading_engine.base.base_broker_adapter import BaseBrokerAdapter
from src.trading_engine.base.base_order import BaseOrder, OrderStatus
from src.trading_engine.broker_adapter.interface import CommissionCalculator, CommissionConfig
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.trade_record.trade_record_manager import TradeRecordManager

logger = logging.getLogger(__name__)


class SimulatedBrokerAdapter(BaseBrokerAdapter):
    """
    模拟券商适配器，用于回测和模拟交易
    根据当前价格立即成交，支持模拟滑点
    """

    def __init__(
        self,
        portfolio_manager: PortfolioManager,
        trade_record_manager: Optional[TradeRecordManager] = None,
        commission_config: Optional[CommissionConfig] = None,
        slippage_rate: float = 0.0001,  # 滑点率，默认万1
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化模拟券商
        Args:
            portfolio_manager: 投资组合管理器
            trade_record_manager: 成交记录管理器
            commission_config: 佣金配置
            slippage_rate: 滑点率，成交价格会偏移这个比例
            config: 其他配置
        """
        super().__init__(config)
        self._portfolio = portfolio_manager
        self._trade_records = trade_record_manager or TradeRecordManager()
        self._commission_calc = CommissionCalculator(commission_config)
        self._slippage_rate = slippage_rate
        self._last_prices: Dict[str, float] = {}
        self.connected = True

    def connect(self) -> bool:
        """连接（模拟连接总是成功）"""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """断开连接"""
        self.connected = False

    def is_connected(self) -> bool:
        """检查是否连接"""
        return self.connected

    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        summary = self._portfolio.get_summary()
        return {
            "total_asset": summary.get("total_asset", 0.0),
            "cash": self._portfolio.get_cash(),
            "market_value": summary.get("total_market_value", 0.0),
            "available_cash": self._portfolio.get_cash(),
            "frozen_cash": 0.0,  # 模拟券商不冻结资金
        }

    def get_available_cash(self) -> float:
        """获取可用资金"""
        return self._portfolio.get_cash()

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有持仓"""
        result = {}
        for pos in self._portfolio.get_non_empty_positions():
            result[pos.ts_code] = {
                "ts_code": pos.ts_code,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "last_price": pos.last_price,
                "market_value": pos.get_market_value(),
                "unrealized_pnl": pos.get_unrealized_pnl(),
            }
        return result

    def get_position(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """获取指定持仓"""
        pos = self._portfolio.get_position(ts_code)
        if pos is None or pos.is_empty():
            return None
        return {
            "ts_code": pos.ts_code,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "last_price": pos.last_price,
            "market_value": pos.get_market_value(),
            "unrealized_pnl": pos.get_unrealized_pnl(),
        }

    def submit_order(self, order: BaseOrder) -> bool:
        """
        提交订单
        模拟券商立即尝试成交，不做价格检查
        """
        if not self.connected:
            logger.warning("券商未连接")
            return False

        # 检查可用资金/持仓
        if order.is_buy():
            commission = self._commission_calc.calculate_buy_commission(
                order.quantity, order.price if order.price else self._last_prices.get(order.ts_code, 0)
            )
            required = (
                order.quantity * (order.price if order.price else self._last_prices.get(order.ts_code, 0)) + commission
            )
            if self._portfolio.get_cash() < required:
                logger.warning(
                    f"资金不足，无法买单: {order.order_id}, 需要 {required}, 可用 {self._portfolio.get_cash()}"
                )
                order.reject()
                return False
        else:
            if not self._portfolio.check_sell_available(order.ts_code, order.quantity):
                logger.warning(f"持仓不足，无法卖单: {order.order_id}")
                order.reject()
                return False

        order.submit()
        # 模拟券商立即成交
        self._execute_order(order)
        return True

    def _execute_order(self, order: BaseOrder) -> None:
        """执行订单成交"""
        # 获取成交价格，应用滑点
        current_price = self._get_execution_price(order)
        if current_price is None:
            logger.error(f"无法获取价格，订单拒绝: {order.order_id}")
            order.reject()
            return

        # 计算佣金
        quantity = order.get_remaining_quantity()
        if order.is_buy():
            commission = self._commission_calc.calculate_buy_commission(quantity, current_price)
        else:
            commission = self._commission_calc.calculate_sell_commission(quantity, current_price)

        # 更新投资组合
        pnl = self._portfolio.process_order_fill(order, quantity, current_price, commission)

        # 记录成交
        pos_before = (
            self._portfolio.get_position(order.ts_code).quantity if self._portfolio.get_position(order.ts_code) else 0
        )
        pos_after = pos_before + (quantity if order.is_buy() else -quantity)

        self._trade_records.add_record(
            order=order,
            filled_quantity=quantity,
            filled_price=current_price,
            filled_time=datetime.now(),
            commission=commission,
            slippage=self._calculate_slippage(order, current_price),
            pnl=pnl if order.is_sell() else None,
            position_before=pos_before,
            position_after=pos_after,
        )

        # 标记成交
        order.fill(quantity, current_price, datetime.now())
        logger.info(f"模拟订单成交: {order.order_id}, {order.ts_code}, {quantity} @ {current_price:.4f}")

    def _get_execution_price(self, order: BaseOrder) -> Optional[float]:
        """获取执行价格，考虑滑点"""
        # 如果订单有限价，使用限价
        if order.order_type in [order.order_type.LIMIT, order.order_type.STOP_LIMIT]:
            return order.price

        # 否则使用最新价格，应用滑点
        if order.ts_code in self._last_prices:
            base_price = self._last_prices[order.ts_code]
        else:
            base_price = self.get_last_price(order.ts_code)
            if base_price is None:
                return None

        # 应用滑点：买入价格上涨，卖出价格下跌
        if order.is_buy():
            return base_price * (1 + self._slippage_rate)
        else:
            return base_price * (1 - self._slippage_rate)

    def _calculate_slippage(self, order: BaseOrder, executed_price: float) -> float:
        """计算滑点金额"""
        if order.ts_code not in self._last_prices:
            return 0.0
        base_price = self._last_prices[order.ts_code]
        return abs(executed_price - base_price) * order.get_remaining_quantity()

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        # 模拟券商所有订单都立即成交，所以不能取消
        logger.debug("模拟券商不支持取消，所有订单立即成交")
        return False

    def query_order(self, order_id: str) -> Optional[BaseOrder]:
        """查询订单状态（不保存订单，返回None）"""
        # 订单由 order_manager 管理
        return None

    def query_orders(
        self,
        status: Optional[List[OrderStatus]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[BaseOrder]:
        """查询订单列表"""
        return []

    def get_last_price(self, ts_code: str) -> Optional[float]:
        """获取最新价格"""
        return self._last_prices.get(ts_code)

    def get_last_prices(self, ts_codes: List[str]) -> Dict[str, Optional[float]]:
        """批量获取最新价格"""
        result = {}
        for ts_code in ts_codes:
            result[ts_code] = self._last_prices.get(ts_code)
        return result

    def update_last_prices(self, prices: Dict[str, float]) -> None:
        """更新最新价格"""
        self._last_prices.update(prices)
        # 更新投资组合中的价格
        self._portfolio.update_prices(prices)

    def get_commission(self, quantity: int, price: float, side: int) -> float:
        """计算佣金"""
        is_buy = side == 1
        return self._commission_calc.calculate_commission(quantity, price, is_buy)

    def get_trade_record_manager(self) -> TradeRecordManager:
        """获取成交记录管理器"""
        return self._trade_records

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok" if self.connected else "disconnected",
            "connected": self.connected,
            "account_id": self.account_id,
            "type": "simulated",
        }
