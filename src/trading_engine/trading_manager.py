"""
统一交易管理器
作为整个交易系统的统一入口，整合所有子模块提供一站式交易服务
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.trading_engine.base.base_order import OrderSide, OrderStatus, OrderType
from src.trading_engine.broker_adapter.broker_adapter_manager import BrokerAdapterManager
from src.trading_engine.broker_adapter.interface import CommissionConfig
from src.trading_engine.broker_adapter.simulated_broker import SimulatedBrokerAdapter
from src.trading_engine.execution_engine.execution_engine import ExecutionEngine
from src.trading_engine.order_management.order import Order
from src.trading_engine.order_management.order_manager import OrderManager
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.risk_control.risk_controller import RiskController
from src.trading_engine.trade_record.trade_record import TradeRecord
from src.trading_engine.trade_record.trade_record_manager import TradeRecordManager
from src.trading_engine.trade_record.trade_statistics import TradeStatistics

logger = logging.getLogger(__name__)


class TradingManager:
    """
    统一交易管理器

    整合所有交易系统子模块，提供一站式交易服务：
    - 订单生命周期管理
    - 投资组合持仓管理
    - 交易记录存储和统计
    - 风险控制检查
    - 算法交易执行
    - 券商适配器管理
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission_config: Optional[CommissionConfig] = None,
        enable_risk_control: bool = True,
        auto_connect_broker: bool = True,
    ):
        """
        初始化统一交易管理器

        Args:
            initial_cash: 初始资金
            commission_config: 佣金配置，None使用默认A股标准
            enable_risk_control: 是否启用风控
            auto_connect_broker: 是否自动连接默认券商
        """
        # 核心子模块初始化
        self._portfolio = PortfolioManager(initial_cash)
        self._order_manager = OrderManager()
        self._trade_recorder = TradeRecordManager()
        self._broker_manager = BrokerAdapterManager()
        self._risk_controller = RiskController() if enable_risk_control else None
        self._execution_engine: Optional[ExecutionEngine] = None

        # 创建默认模拟券商
        if auto_connect_broker:
            self._init_default_simulated_broker(commission_config)

        # 统计信息
        self._start_time = datetime.now()

    def _init_default_simulated_broker(self, commission_config: Optional[CommissionConfig]) -> None:
        """初始化默认模拟券商"""
        broker = SimulatedBrokerAdapter(
            portfolio_manager=self._portfolio,
            trade_record_manager=self._trade_recorder,
            commission_config=commission_config,
        )
        self._broker_manager.register_adapter("default", broker, default=True)
        self._broker_manager.connect_all()

        # 初始化执行引擎
        default_broker = self._broker_manager.get_default_adapter()
        if default_broker is not None:
            self._execution_engine = ExecutionEngine(
                broker_adapter=default_broker,
                order_manager=self._order_manager,
                portfolio_manager=self._portfolio,
            )

    def submit_order(
        self,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        strategy_id: Optional[str] = None,
        stop_price: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        提交新订单

        Args:
            ts_code: 股票代码
            side: 买卖方向
            quantity: 数量
            price: 价格（市价单可为None）
            order_type: 订单类型
            strategy_id: 策略ID
            stop_price: 触发价（止损单需要）
            **kwargs: 额外风控参数（limit_up, limit_down, is_suspended, is_delisted等）

        Returns:
            提交结果字典
        """
        # 1. 创建订单对象
        try:
            if order_type == OrderType.MARKET:
                order = Order.create_market_order(ts_code, side, quantity, strategy_id)
            elif order_type == OrderType.LIMIT:
                order = Order.create_limit_order(ts_code, side, quantity, price, strategy_id)
            elif order_type == OrderType.STOP:
                order = Order.create_stop_order(ts_code, side, quantity, stop_price, strategy_id)
            elif order_type == OrderType.STOP_LIMIT:
                order = Order.create_stop_limit_order(
                    ts_code,
                    side,
                    quantity,
                    price,
                    stop_price,
                    strategy_id,
                )
            else:
                return {
                    "success": False,
                    "message": f"不支持的订单类型: {order_type}",
                    "order_id": None,
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"创建订单失败: {str(e)}",
                "order_id": None,
            }

        # 2. 风控检查
        check_price = price if price is not None else 0.0
        if self._risk_controller:
            risk_result = self._risk_controller.check_order(
                ts_code=ts_code,
                side=side,
                quantity=quantity,
                price=check_price,
                portfolio=self._portfolio,
                **kwargs,
            )
            if not risk_result.passed:
                return {
                    "success": False,
                    "message": risk_result.message,
                    "order_id": order.order_id,
                    "risk_result": risk_result,
                }

        # 3. 提交订单到订单管理器
        self._order_manager.add_order(order)
        order.submit()

        # 4. 提交订单到券商
        broker = self._broker_manager.get_default_adapter()
        if broker is None:
            return {
                "success": False,
                "message": "没有可用的券商适配器",
                "order_id": order.order_id,
            }

        # 如果有价格，更新到券商（模拟券商需要）
        if price is not None:
            broker.update_last_prices({ts_code: price})

        broker_result = broker.submit_order(order)
        if not broker_result:
            order.reject()
            return {
                "success": False,
                "message": "券商拒绝订单",
                "order_id": order.order_id,
            }

        # 模拟券商已经立即成交，不需要额外处理
        # 真实券商需要等待成交回报，这里不处理

        return {
            "success": True,
            "message": "订单提交成功",
            "order_id": order.order_id,
            "order": order,
        }

    def _process_filled_order(
        self,
        order: Order,
        filled_price: Optional[float],
    ) -> None:
        """处理已成交订单，更新持仓和记录"""
        # 获取成交信息
        filled_quantity = order.get_filled_quantity()
        price = filled_price if filled_price is not None else order.price
        if price is None:
            price = self._get_last_price(order.ts_code)
        filled_time = datetime.now()

        # 计算佣金和费用
        broker = self._broker_manager.get_default_adapter()
        commission = 0.0
        if broker is not None:
            commission = broker.get_commission(
                order.ts_code,
                order.side,
                filled_quantity,
                price,
            )

        # 更新投资组合持仓
        self._portfolio.on_order_filled(
            ts_code=order.ts_code,
            side=order.side,
            filled_quantity=filled_quantity,
            filled_price=price,
            commission=commission,
        )

        # 同步持仓到模拟券商
        if isinstance(broker, SimulatedBrokerAdapter):
            positions = self._portfolio.get_all_positions()
            cash = self._portfolio.get_available_cash()
            broker.sync_portfolio(positions, cash)

        # 创建成交记录
        trade = TradeRecord(
            order_id=order.order_id,
            ts_code=order.ts_code,
            side=order.side,
            quantity=filled_quantity,
            filled_price=price,
            filled_time=filled_time,
            commission=commission,
            strategy_id=order.strategy_id,
        )
        self._trade_recorder.add_trade(trade)

    def _get_last_price(self, ts_code: str) -> float:
        """获取股票最新价格"""
        position = self._portfolio.get_position(ts_code)
        if position is not None:
            return position.last_price
        # 如果没有持仓，返回0，应该不会到这里
        return 0.0

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        取消订单

        Args:
            order_id: 订单ID

        Returns:
            取消结果
        """
        order = self._order_manager.get_order(order_id)
        if order is None:
            return {
                "success": False,
                "message": f"订单不存在: {order_id}",
            }

        if not order.can_cancel():
            return {
                "success": False,
                "message": f"订单状态不允许取消: {order.status}",
            }

        # 券商端取消
        broker = self._broker_manager.get_default_adapter()
        if broker is not None:
            result = broker.cancel_order(order_id)
            if not result["success"]:
                return result

        order.cancel()
        return {
            "success": True,
            "message": "订单取消成功",
            "order": order,
        }

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self._order_manager.get_order(order_id)

    def get_all_orders(self) -> List[Order]:
        """获取所有订单"""
        return self._order_manager.get_all_orders()

    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """按状态查询订单"""
        return self._order_manager.query_orders(status=[status])

    def get_position(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """获取单个持仓"""
        position = self._portfolio.get_position(ts_code)
        if position is None:
            return None
        return position.to_dict()

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有持仓"""
        positions = self._portfolio.get_all_positions()
        return {ts_code: pos.to_dict() for ts_code, pos in positions.items()}

    def get_portfolio_summary(self) -> Dict[str, float]:
        """获取投资组合汇总信息"""
        return self._portfolio.get_summary()

    def get_total_asset(self) -> float:
        """获取总资产"""
        summary = self._portfolio.get_summary()
        return summary.get("total_asset", 0.0)

    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        summary = self._portfolio.get_summary()
        return summary.get("total_pnl", 0.0)

    def get_all_trades(self) -> List[TradeRecord]:
        """获取所有成交记录"""
        return self._trade_recorder.get_all_records()

    def get_trades_by_strategy(self, strategy_id: str) -> List[TradeRecord]:
        """按策略查询成交记录"""
        return self._trade_recorder.query_records(strategy_id=strategy_id)

    def get_trading_statistics(self) -> Dict[str, Any]:
        """获取交易统计分析"""
        trades = self._trade_recorder.get_all_records()
        return TradeStatistics.generate_full_report(trades)

    def submit_vwap_order(
        self,
        ts_code: str,
        side: OrderSide,
        total_quantity: int,
        start_time: datetime,
        end_time: datetime,
        participation_rate: float = 0.1,
        strategy_id: Optional[str] = None,
        min_chunk: int = 100,
        max_chunk: int = 10000,
        num_splits: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        提交VWAP算法订单

        Args:
            ts_code: 股票代码
            side: 买卖方向
            total_quantity: 总数量
            start_time: 开始时间
            end_time: 结束时间
            participation_rate: 参与率（未使用，保留参数兼容）
            strategy_id: 策略ID
            min_chunk: 最小单笔数量
            max_chunk: 最大单笔数量
            num_splits: 拆分份数，None自动计算
            **kwargs: 风控参数（limit_up, limit_down等）

        Returns:
            提交结果
        """
        # 风控检查
        if self._risk_controller:
            # 使用当前价格估算
            # 这里简化处理，实际执行时每笔拆分订单会再次风控检查
            approx_price = kwargs.get("current_price", 0.0)
            risk_result = self._risk_controller.check_order(
                ts_code=ts_code,
                side=side,
                quantity=total_quantity,
                price=approx_price,
                portfolio=self._portfolio,
                **kwargs,
            )
            if not risk_result.passed:
                return {
                    "success": False,
                    "message": risk_result.message,
                    "execution_id": None,
                }

        # 提交到执行引擎
        execution_id = self._execution_engine.submit_vwap(
            ts_code=ts_code,
            side=side,
            total_quantity=total_quantity,
            start_time=start_time,
            end_time=end_time,
            strategy_id=strategy_id,
            min_chunk=min_chunk,
            max_chunk=max_chunk,
            num_splits=num_splits,
        )

        return {
            "success": True,
            "message": "VWAP算法订单提交成功",
            "execution_id": execution_id,
        }

    def submit_twap_order(
        self,
        ts_code: str,
        side: OrderSide,
        total_quantity: int,
        start_time: datetime,
        end_time: datetime,
        interval_seconds: int = 300,
        strategy_id: Optional[str] = None,
        min_chunk: int = 100,
        max_chunk: int = 10000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        提交TWAP算法订单

        Args:
            ts_code: 股票代码
            side: 买卖方向
            total_quantity: 总数量
            start_time: 开始时间
            end_time: 结束时间
            interval_seconds: 间隔秒数
            strategy_id: 策略ID
            min_chunk: 最小单笔数量
            max_chunk: 最大单笔数量
            **kwargs: 风控参数（limit_up, limit_down等）

        Returns:
            提交结果
        """
        # 风控检查
        if self._risk_controller:
            # 使用当前价格估算
            # 这里简化处理，实际执行时每笔拆分订单会再次风控检查
            approx_price = kwargs.get("current_price", 0.0)
            risk_result = self._risk_controller.check_order(
                ts_code=ts_code,
                side=side,
                quantity=total_quantity,
                price=approx_price,
                portfolio=self._portfolio,
                **kwargs,
            )
            if not risk_result.passed:
                return {
                    "success": False,
                    "message": risk_result.message,
                    "execution_id": None,
                }

        # 提交到执行引擎
        execution_id = self._execution_engine.submit_twap(
            ts_code=ts_code,
            side=side,
            total_quantity=total_quantity,
            start_time=start_time,
            end_time=end_time,
            strategy_id=strategy_id,
            interval_seconds=interval_seconds,
            min_chunk=min_chunk,
            max_chunk=max_chunk,
        )

        return {
            "success": True,
            "message": "TWAP算法订单提交成功",
            "execution_id": execution_id,
        }

    def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """取消算法执行"""
        success = self._execution_engine.cancel_execution(execution_id)
        if success:
            return {"success": True, "message": "算法执行已取消"}
        else:
            return {"success": False, "message": "取消失败，执行不存在"}

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行引擎统计"""
        return self._execution_engine.get_statistics()

    def update_last_prices(self, prices: Dict[str, float]) -> None:
        """更新最新价格"""
        self._portfolio.update_prices(prices)
        broker = self._broker_manager.get_default_adapter()
        if broker is not None and isinstance(broker, SimulatedBrokerAdapter):
            broker.update_last_prices(prices)

    def check_portfolio_risk(self, max_drawdown: float = 0.2) -> Dict[str, Any]:
        """检查投资组合整体风险"""
        if self._risk_controller:
            return self._risk_controller.check_portfolio_risk(
                self._portfolio,
                max_drawdown,
            )
        return {"alert": False, "message": "风控未启用"}

    def register_custom_broker(
        self,
        name: str,
        broker,
        default: bool = False,
    ) -> None:
        """注册自定义券商适配器"""
        self._broker_manager.register_adapter(name, broker, default_adapter=default)

    def get_broker_manager(self) -> BrokerAdapterManager:
        """获取券商适配器管理器"""
        return self._broker_manager

    def get_order_manager(self) -> OrderManager:
        """获取订单管理器"""
        return self._order_manager

    def get_portfolio_manager(self) -> PortfolioManager:
        """获取投资组合管理器"""
        return self._portfolio

    def get_trade_record_manager(self) -> TradeRecordManager:
        """获取成交记录管理器"""
        return self._trade_recorder

    def get_risk_controller(self) -> Optional[RiskController]:
        """获取风险控制器"""
        return self._risk_controller

    def get_execution_engine(self) -> ExecutionEngine:
        """获取执行引擎"""
        return self._execution_engine

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        uptime = (datetime.now() - self._start_time).total_seconds()

        portfolio_health = self._portfolio.health_check()
        order_health = self._order_manager.health_check()
        trade_health = self._trade_recorder.health_check()
        broker_health = self._broker_manager.health_check_all()
        execution_health = self._execution_engine.health_check()

        all_ok = (
            portfolio_health["status"] == "ok"
            and order_health["status"] == "ok"
            and trade_health["status"] == "ok"
            and all(adapter["status"] == "ok" for name, adapter in broker_health.items())
            and execution_health["status"] == "ok"
        )

        return {
            "status": "ok" if all_ok else "degraded",
            "uptime_seconds": uptime,
            "portfolio": portfolio_health,
            "order_manager": order_health,
            "trade_recorder": trade_health,
            "broker_manager": broker_health,
            "execution_engine": execution_health,
            "stats": {
                "total_orders": len(self._order_manager.get_all_orders()),
                "active_orders": len(self._order_manager.get_active_orders()),
                "total_positions": len(self._portfolio.get_all_positions()),
                "total_trades": len(self._trade_recorder.get_all_records()),
                "running_executions": len(self._execution_engine._active_executions),
            },
        }
