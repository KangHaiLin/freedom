"""
执行引擎
负责接收算法订单，调度算法执行，提交订单到券商
"""

import logging
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from typing import Any, Dict, List, Optional

from src.trading_engine.base.base_broker_adapter import BaseBrokerAdapter
from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.execution_engine.twap_algo import TWAPAlgo
from src.trading_engine.execution_engine.vwap_algo import VWAPAlgo
from src.trading_engine.order_management.order_manager import OrderManager
from src.trading_engine.position_management.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


class ExecutionAlgo:
    """执行算法类型"""

    VWAP = "vwap"
    TWAP = "twap"


class ActiveExecution:
    """活跃执行订单"""

    def __init__(
        self,
        order_id: str,
        ts_code: str,
        side: OrderSide,
        total_quantity: int,
        algo: Any,
        created_time: datetime,
    ):
        self.order_id = order_id
        self.ts_code = ts_code
        self.side = side
        self.total_quantity = total_quantity
        self.algo = algo
        self.created_time = created_time
        self.started: bool = False
        self.last_check_time: Optional[datetime] = None


class ExecutionEngine:
    """
    执行引擎主类
    管理算法订单执行，调度算法，提交小单到券商
    """

    def __init__(
        self,
        broker_adapter: BaseBrokerAdapter,
        order_manager: OrderManager,
        portfolio_manager: PortfolioManager,
        poll_interval: float = 1.0,  # 轮询间隔秒
        auto_start: bool = True,
    ):
        """
        初始化执行引擎
        Args:
            broker_adapter: 券商适配器
            order_manager: 订单管理器
            portfolio_manager: 投资组合管理器
            poll_interval: 轮询间隔
            auto_start: 是否自动启动后台线程
        """
        self._broker = broker_adapter
        self._order_manager = order_manager
        self._portfolio = portfolio_manager
        self._poll_interval = poll_interval

        self._active_executions: Dict[str, ActiveExecution] = {}
        self._queue: Queue = Queue()
        self._running: bool = False
        self._thread: Optional[Thread] = None

        if auto_start:
            self.start()

    def start(self) -> None:
        """启动后台执行线程"""
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._execution_loop, daemon=True)
        self._thread.start()
        logger.info("执行引擎后台线程已启动")

    def stop(self) -> None:
        """停止后台执行线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("执行引擎后台线程已停止")

    def is_running(self) -> bool:
        """检查是否运行"""
        return self._running

    def submit_vwap(
        self,
        ts_code: str,
        side: OrderSide,
        total_quantity: int,
        start_time: datetime,
        end_time: datetime,
        strategy_id: Optional[str] = None,
        min_chunk: int = 100,
        max_chunk: int = 10000,
        num_splits: Optional[int] = None,
    ) -> str:
        """
        提交VWAP算法执行
        Args:
            ts_code: 股票代码
            side: 买卖方向
            total_quantity: 总数量
            start_time: 开始时间
            end_time: 结束时间
            strategy_id: 策略ID
            min_chunk: 最小单笔
            max_chunk: 最大单笔
            num_splits: 拆分份数
        Returns:
            执行ID
        """
        order = Order.create_market_order(ts_code, side, total_quantity, strategy_id)
        order_id = self._order_manager.add_order(order)
        order.submit()

        vwap = VWAPAlgo(
            total_quantity=total_quantity,
            side=side,
            start_time=start_time,
            end_time=end_time,
            min_chunk=min_chunk,
            max_chunk=max_chunk,
            num_splits=num_splits,
        )

        exec_id = order_id
        active = ActiveExecution(
            order_id=order_id,
            ts_code=ts_code,
            side=side,
            total_quantity=total_quantity,
            algo=vwap,
            created_time=datetime.now(),
        )
        self._active_executions[exec_id] = active
        logger.info(f"提交VWAP执行: {exec_id}, {ts_code}, {total_quantity}")
        return exec_id

    def submit_twap(
        self,
        ts_code: str,
        side: OrderSide,
        total_quantity: int,
        start_time: datetime,
        end_time: datetime,
        strategy_id: Optional[str] = None,
        interval_seconds: float = 300,
        min_chunk: int = 100,
        max_chunk: int = 10000,
    ) -> str:
        """
        提交TWAP算法执行
        Args:
            ts_code: 股票代码
            side: 买卖方向
            total_quantity: 总数量
            start_time: 开始时间
            end_time: 结束时间
            strategy_id: 策略ID
            interval_seconds: 间隔秒数
            min_chunk: 最小单笔
            max_chunk: 最大单笔
        Returns:
            执行ID
        """
        order = Order.create_market_order(ts_code, side, total_quantity, strategy_id)
        order_id = self._order_manager.add_order(order)
        order.submit()

        twap = TWAPAlgo(
            total_quantity=total_quantity,
            side=side,
            start_time=start_time,
            end_time=end_time,
            interval_seconds=interval_seconds,
            min_chunk=min_chunk,
            max_chunk=max_chunk,
        )

        exec_id = order_id
        active = ActiveExecution(
            order_id=order_id,
            ts_code=ts_code,
            side=side,
            total_quantity=total_quantity,
            algo=twap,
            created_time=datetime.now(),
        )
        self._active_executions[exec_id] = active
        logger.info(f"提交TWAP执行: {exec_id}, {ts_code}, {total_quantity}")
        return exec_id

    def cancel_execution(self, exec_id: str) -> bool:
        """
        取消执行
        Args:
            exec_id: 执行ID
        Returns:
            是否取消成功
        """
        if exec_id not in self._active_executions:
            return False
        del self._active_executions[exec_id]
        logger.info(f"取消执行: {exec_id}")
        return True

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """获取所有活跃执行"""
        result = []
        for exec_id, exec in self._active_executions.items():
            result.append(
                {
                    "exec_id": exec_id,
                    "order_id": exec.order_id,
                    "ts_code": exec.ts_code,
                    "side": exec.side.name,
                    "total_quantity": exec.total_quantity,
                    "progress": exec.algo.get_progress(),
                    "remaining": exec.algo.get_remaining_quantity(),
                    "done": exec.algo.is_done(),
                    "created_time": exec.created_time.isoformat(),
                }
            )
        return result

    def _execution_loop(self) -> None:
        """执行循环，后台线程运行"""
        while self._running:
            self._check_active_executions()
            # 休眠
            try:
                self._queue.get(timeout=self._poll_interval)
            except Empty:
                continue

    def _check_active_executions(self) -> None:
        """检查所有活跃执行，生成需要下单的"""
        done_ids = []
        now = datetime.now()

        for exec_id, active in self._active_executions.items():
            if active.algo.is_done():
                done_ids.append(exec_id)
                continue

            chunk = self._get_next_chunk(active, now)
            if chunk is not None and chunk > 0:
                self._execute_chunk(active, chunk)
                if active.algo.is_done():
                    done_ids.append(exec_id)

            active.last_check_time = now

        # 清理已完成
        for exec_id in done_ids:
            if exec_id in self._active_executions:
                logger.info(f"执行完成: {exec_id}")
                del self._active_executions[exec_id]

    def _get_next_chunk(self, active: ActiveExecution, now: datetime) -> Optional[int]:
        """获取下一个需要执行的chunk"""
        if isinstance(active.algo, (VWAPAlgo, TWAPAlgo)):
            return active.algo.get_next_order(now)
        return None

    def _execute_chunk(self, active: ActiveExecution, chunk: int) -> None:
        """执行一个chunk"""
        order = Order.create_market_order(
            ts_code=active.ts_code,
            side=active.side,
            quantity=chunk,
        )
        order_id = self._order_manager.add_order(order)
        success = self._broker.submit_order(order)
        if not success:
            logger.warning(f"Chunk执行失败: {order_id}, {chunk}")
            # 失败了把数量加回去
            if hasattr(active.algo, "remaining_quantity"):
                active.algo.remaining_quantity += chunk

    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            "active_executions": len(self._active_executions),
            "running": self._running,
            "poll_interval": self._poll_interval,
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok" if self._running else "stopped",
            "active_count": len(self._active_executions),
            "thread_alive": self._thread.is_alive() if self._thread else False,
        }
