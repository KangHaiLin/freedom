"""
风险扫描器
负责定期扫描全系统各类风险
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.risk_management.rule_engine.rule_executor import RuleExecutor
from src.risk_management.rule_engine.rule_result import RuleResult

from .alert_generator import AlertGenerator, AlertLevel

logger = logging.getLogger(__name__)


class RealtimeRiskScanner:
    """
    实时风险扫描器
    定期扫描各类风险，发现风险立即生成告警
    """

    def __init__(
        self,
        rule_executor: RuleExecutor,
        alert_generator: AlertGenerator,
        scan_interval_seconds: int = 1,
    ):
        """
        初始化风险扫描器

        Args:
            rule_executor: 规则执行器
            alert_generator: 告警生成器
            scan_interval_seconds: 扫描间隔（秒），默认每秒一次
        """
        self._rule_executor = rule_executor
        self._alert_generator = alert_generator
        self._scan_interval = scan_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # 数据获取回调 - 需要外部注入
        self._get_recent_trades_callback: Optional[callable] = None
        self._get_all_positions_callback: Optional[callable] = None
        self._get_market_data_callback: Optional[callable] = None

    def register_recent_trades_callback(self, callback: callable) -> None:
        """注册获取最近交易回调"""
        self._get_recent_trades_callback = callback

    def register_all_positions_callback(self, callback: callable) -> None:
        """注册获取所有持仓回调"""
        self._get_all_positions_callback = callback

    def register_market_data_callback(self, callback: callable) -> None:
        """注册获取市场数据回调"""
        self._get_market_data_callback = callback

    async def start(self) -> None:
        """启动扫描"""
        if self._running:
            logger.warning("Risk scanner already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("Realtime risk scanner started")

    async def stop(self) -> None:
        """停止扫描"""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Realtime risk scanner stopped")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running

    async def _scan_loop(self) -> None:
        """扫描主循环"""
        while self._running:
            start_time = datetime.now()
            try:
                await self._scan_all_risks()
            except Exception as e:
                logger.error(f"Error in risk scan loop: {e}", exc_info=True)
            # 控制扫描频率
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed < self._scan_interval:
                await asyncio.sleep(self._scan_interval - elapsed)

    async def _scan_all_risks(self) -> None:
        """扫描所有风险类型"""
        # 1. 交易风险扫描
        await self._scan_trade_risks()
        # 2. 持仓风险扫描
        await self._scan_position_risks()
        # 3. 市场风险扫描
        await self._scan_market_risks()
        # 4. 操作风险扫描
        await self._scan_operation_risks()

    async def _scan_trade_risks(self) -> None:
        """扫描交易风险"""
        if self._get_recent_trades_callback is None:
            return

        try:
            recent_trades = self._get_recent_trades_callback()
            for trade in recent_trades:
                result = self._rule_executor.execute("intraday_trade", trade)
                self._process_result("trade", trade, result)
        except Exception as e:
            logger.error(f"Error scanning trade risks: {e}")

    async def _scan_position_risks(self) -> None:
        """扫描持仓风险"""
        if self._get_all_positions_callback is None:
            return

        try:
            all_positions = self._get_all_positions_callback()
            for position in all_positions:
                result = self._rule_executor.execute("position_risk", position)
                self._process_result("position", position, result)

                # 额外检查持仓风险值，如果高于阈值直接告警
                risk_value = position.get("risk_value", 0.0)
                if risk_value > 0.8:
                    self._alert_generator.generate(
                        level=AlertLevel.WARNING,
                        message=f"持仓风险值过高: {risk_value:.2f}",
                        data={"ts_code": position.get("ts_code"), "risk_value": risk_value},
                        risk_type="position_high_risk",
                    )
        except Exception as e:
            logger.error(f"Error scanning position risks: {e}")

    async def _scan_market_risks(self) -> None:
        """扫描市场风险"""
        if self._get_market_data_callback is None:
            return

        try:
            market_data = self._get_market_data_callback()
            result = self._rule_executor.execute("market_risk", market_data)
            self._process_result("market", market_data, result)
        except Exception as e:
            logger.error(f"Error scanning market risks: {e}")

    async def _scan_operation_risks(self) -> None:
        """扫描操作风险"""
        try:
            # 检查系统操作风险，比如API调用错误率、延迟等
            result = self._rule_executor.execute("operation_risk", {})
            self._process_result("operation", {}, result)
        except Exception as e:
            logger.error(f"Error scanning operation risks: {e}")

    def _process_result(
        self,
        risk_type: str,
        data: Dict[str, Any],
        result: RuleResult,
    ) -> None:
        """处理规则检查结果"""
        if not result.has_violations():
            return

        for violation in result.get_violations():
            level_map = {
                AlertLevel.INFO: AlertLevel.INFO,
                AlertLevel.WARNING: AlertLevel.WARNING,
                AlertLevel.ERROR: AlertLevel.ERROR,
                AlertLevel.CRITICAL: AlertLevel.CRITICAL,
            }
            level = level_map.get(violation.level, AlertLevel.WARNING)
            self._alert_generator.generate(
                level=level,
                message=violation.message,
                data={
                    "risk_type": risk_type,
                    "context_data": data,
                    **violation.details,
                },
                violation=violation,
                risk_type=f"{risk_type}_{violation.rule_id}",
            )

    def scan_once(self) -> Dict[str, Any]:
        """同步单次扫描，用于手动触发"""
        # 执行一次完整扫描
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self._scan_all_risks())
        stats = self.get_statistics()
        return {
            "success": True,
            "stats": stats,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取扫描统计"""
        return {
            "running": self._running,
            "scan_interval": self._scan_interval,
            "total_alerts": len(self._alert_generator.get_recent_alerts()),
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.get_statistics()
        return {
            "status": "ok" if self._running else "stopped",
            "stats": stats,
        }
