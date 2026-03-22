"""
统一风险管理管理器
作为风险管理子系统的统一入口，整合所有子模块提供一站式风险管控服务
"""

import logging
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from src.risk_management.audit_trail.operation_logger import OperationLogger, OperationType
from src.risk_management.audit_trail.risk_event_store import RiskEvent, RiskEventStore
from src.risk_management.base.base_rule import BaseRule, RuleLevel
from src.risk_management.compliance_management.abnormal_detector import AbnormalTradeDetector
from src.risk_management.compliance_management.compliance_checker import ComplianceChecker
from src.risk_management.compliance_management.report_generator import ComplianceReportGenerator
from src.risk_management.realtime_monitor.alert_generator import Alert, AlertGenerator
from src.risk_management.realtime_monitor.risk_scanner import RealtimeRiskScanner
from src.risk_management.risk_calculation.limit_manager import LimitManager, LimitType, RiskLimit
from src.risk_management.risk_calculation.scenario_analyzer import ScenarioAnalyzer
from src.risk_management.risk_calculation.stress_tester import StressTester
from src.risk_management.risk_calculation.var_calculator import VaRCalculator
from src.risk_management.rule_engine.builtins import get_default_pre_trade_rules
from src.risk_management.rule_engine.rule import Rule, RuleVersion
from src.risk_management.rule_engine.rule_executor import RuleExecutor
from src.risk_management.rule_engine.rule_manager import RuleManager
from src.risk_management.rule_engine.rule_result import RuleResult, RuleViolation

logger = logging.getLogger(__name__)


class RiskManager:
    """
    统一风险管理管理器
    整合所有风控子模块，提供一站式风险管控服务

    职责：
    - 交易前风控检查
    - 实时风险监控
    - 合规检查和报表生成
    - 风险计算（VaR、压力测试、情景分析）
    - 风险限额管理
    - 审计跟踪
    """

    def __init__(
        self,
        load_default_rules: bool = True,
        enable_realtime_monitor: bool = True,
    ):
        """
        初始化风险管理管理器

        Args:
            load_default_rules: 是否加载默认预定义规则
            enable_realtime_monitor: 是否启用实时监控
        """
        # ========== 规则引擎 ==========
        self._rule_manager = RuleManager()
        self._rule_executor = RuleExecutor(self._rule_manager)

        # 加载默认规则
        if load_default_rules:
            self._load_default_rules()

        # ========== 实时监控 ==========
        self._alert_generator = AlertGenerator()
        self._realtime_scanner = (
            RealtimeRiskScanner(
                self._rule_executor,
                self._alert_generator,
            )
            if enable_realtime_monitor
            else None
        )

        # ========== 合规管理 ==========
        self._compliance_checker = ComplianceChecker(self._rule_executor)
        self._abnormal_detector = AbnormalTradeDetector()
        self._report_generator = ComplianceReportGenerator()

        # ========== 风险计算 ==========
        self._var_calculator = VaRCalculator()
        self._stress_tester = StressTester()
        self._scenario_analyzer = ScenarioAnalyzer()
        self._limit_manager = LimitManager()
        # 设置默认限额
        self._limit_manager.set_default_limits()

        # ========== 审计跟踪 ==========
        self._operation_logger = OperationLogger()
        self._risk_event_store = RiskEventStore()

        # 加载历史日志
        self._operation_logger.load_from_file()

        logger.info("RiskManager initialized")

    def pre_trade_check(
        self,
        user_id: int,
        ts_code: str,
        side: str,
        price: float,
        quantity: int,
        **kwargs,
    ) -> RuleResult:
        """
        交易前风控检查

        Args:
            user_id: 用户ID
            ts_code: 股票代码
            side: 买卖方向
            price: 价格
            quantity: 数量
            **kwargs: 额外上下文信息

        Returns:
            检查结果
        """
        context = {
            "user_id": user_id,
            "ts_code": ts_code,
            "side": side,
            "price": price,
            "quantity": quantity,
            **kwargs,
        }
        result = self._rule_executor.execute("pre_trade", context, user_id)

        # 记录风险事件
        if not result.passed():
            for violation in result.get_violations():
                self._risk_event_store.add_from_violation(
                    violation=violation,
                    event_type="pre_trade",
                    user_id=user_id,
                    ts_code=ts_code,
                )

        # 记录操作日志
        self._operation_logger.log(
            operation_type=OperationType.RISK_CHECK,
            operator_id=user_id,
            details={
                "ts_code": ts_code,
                "side": side,
                "price": price,
                "quantity": quantity,
                "passed": result.passed(),
                "violations": len(result.get_violations()),
            },
        )

        return result

    def add_rule(
        self,
        rule: Rule,
        created_by: int,
    ) -> RuleVersion:
        """
        添加规则

        Args:
            rule: 规则对象
            created_by: 创建者ID

        Returns:
            版本信息
        """
        version = self._rule_manager.add_rule(rule, created_by)

        # 记录操作日志
        self._operation_logger.log(
            operation_type=OperationType.RULE_CREATE if version.version_id == "1" else OperationType.RULE_UPDATE,
            operator_id=created_by,
            details={
                "rule_id": rule.rule_id,
                "version_id": version.version_id,
            },
        )

        return version

    def enable_rule(
        self,
        rule_id: str,
        operator_id: int,
    ) -> bool:
        """启用规则"""
        result = self._rule_manager.enable_rule(rule_id)

        if result:
            self._operation_logger.log(
                operation_type=OperationType.RULE_ENABLE,
                operator_id=operator_id,
                details={"rule_id": rule_id},
            )

        return result

    def disable_rule(
        self,
        rule_id: str,
        operator_id: int,
    ) -> bool:
        """禁用规则"""
        result = self._rule_manager.disable_rule(rule_id)

        if result:
            self._operation_logger.log(
                operation_type=OperationType.RULE_DISABLE,
                operator_id=operator_id,
                details={"rule_id": rule_id},
            )

        return result

    def delete_rule(
        self,
        rule_id: str,
        operator_id: int,
    ) -> bool:
        """删除规则"""
        result = self._rule_manager.delete_rule(rule_id)

        if result:
            self._operation_logger.log(
                operation_type=OperationType.RULE_DELETE,
                operator_id=operator_id,
                details={"rule_id": rule_id},
            )

        return result

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """获取规则"""
        return self._rule_manager.get_rule(rule_id)

    def list_all_rules(self) -> List[Rule]:
        """列出所有规则"""
        return self._rule_manager.get_all_rules()

    # ========== 实时监控 ==========

    def start_realtime_monitor(self) -> None:
        """启动实时风险监控"""
        if self._realtime_scanner:
            import asyncio

            asyncio.create_task(self._realtime_scanner.start())
            logger.info("Realtime risk monitor started")

    def stop_realtime_monitor(self) -> None:
        """停止实时风险监控"""
        if self._realtime_scanner:
            import asyncio

            asyncio.create_task(self._realtime_scanner.stop())
            logger.info("Realtime risk monitor stopped")

    def register_recent_trades_callback(self, callback: Callable) -> None:
        """注册获取最近交易回调"""
        if self._realtime_scanner:
            self._realtime_scanner.register_recent_trades_callback(callback)

    def register_positions_callback(self, callback: Callable) -> None:
        """注册获取所有持仓回调"""
        if self._realtime_scanner:
            self._realtime_scanner.register_all_positions_callback(callback)

    def get_recent_alerts(self, count: int = 100) -> List[Alert]:
        """获取最近告警"""
        return self._alert_generator.get_recent_alerts(count)

    # ========== 合规检查 ==========

    def compliance_check_t1(
        self,
        available_quantity: int,
        sell_quantity: int,
        today_bought: int,
    ) -> Dict[str, Any]:
        """检查T+1限制"""
        return self._compliance_checker.check_t1_restriction(available_quantity, sell_quantity, today_bought)

    def compliance_check_price_limit(
        self,
        price: float,
        limit_up: float,
        limit_down: float,
    ) -> Dict[str, Any]:
        """检查价格涨跌停限制"""
        return self._compliance_checker.check_price_limit(price, limit_up, limit_down)

    def detect_abnormal_trades(
        self,
        trades: List[Dict[str, Any]],
        positions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """检测异常交易"""
        return self._abnormal_detector.detect_all(trades, positions)

    def generate_compliance_daily_report(
        self,
        report_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """生成合规日报"""
        return self._report_generator.generate_daily_report(report_date)

    def generate_compliance_monthly_report(
        self,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """生成合规月报"""
        return self._report_generator.generate_monthly_report(year, month)

    # ========== 风险计算 ==========

    def calculate_var(
        self,
        returns,
        portfolio_value: float,
        method: str = "historical",
    ) -> Dict[str, Any]:
        """计算VaR风险价值"""
        if method == "parametric":
            return self._var_calculator.parametric_var(returns, portfolio_value)
        elif method == "historical":
            return self._var_calculator.historical_simulation(returns, portfolio_value)
        elif method == "monte_carlo":
            return self._var_calculator.monte_carlo_simulation(returns, portfolio_value)
        else:
            raise ValueError(f"Unknown method: {method}")

    def run_stress_test(
        self,
        scenario_id: str,
        current_positions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行压力测试"""
        return self._stress_tester.run_stress_test(scenario_id, current_positions)

    def run_scenario_analysis(
        self,
        scenario_id: str,
        exposures: Dict[str, float],
        current_value: float,
    ) -> Dict[str, Any]:
        """执行情景分析"""
        return self._scenario_analyzer.analyze(scenario_id, exposures, current_value)

    def check_limit(
        self,
        limit_type: str,
        current_value: float,
        user_id: Optional[int] = None,
        ts_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """检查是否超过风险限额"""
        return self._limit_manager.check_limit(limit_type, current_value, user_id, ts_code)

    def add_limit(self, limit: RiskLimit) -> int:
        """添加风险限额"""
        limit_id = self._limit_manager.add_limit(limit)
        self._operation_logger.log(
            operation_type=OperationType.LIMIT_UPDATE,
            operator_id=1,  # system
            details={
                "limit_id": limit_id,
                "limit_type": limit.limit_type,
                "limit_value": limit.limit_value,
            },
        )
        return limit_id

    def reset_daily_limits(self) -> None:
        """重置每日限额使用统计（每日开盘调用）"""
        self._limit_manager.reset_daily_usage()

    # ========== 审计查询 ==========

    def query_risk_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs,
    ) -> List[RiskEvent]:
        """查询风险事件"""
        return self._risk_event_store.query_events(start_date=start_date, end_date=end_date, **kwargs)

    def get_risk_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """获取风险统计"""
        return self._risk_event_store.get_statistics(start_date, end_date)

    def query_operation_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        **kwargs,
    ) -> List:
        """查询操作日志"""
        return self._operation_logger.query_logs(start_time=start_time, end_time=end_time, **kwargs)

    def mark_event_handled(
        self,
        event_id: int,
        handled_by: int,
        note: str,
    ) -> bool:
        """标记风险事件已处理"""
        result = self._risk_event_store.mark_handled(event_id, handled_by, note)

        if result:
            self._operation_logger.log(
                operation_type=OperationType.VIOLATION_HANDLE,
                operator_id=handled_by,
                details={
                    "event_id": event_id,
                    "note": note,
                },
            )

        return result

    # ========== 健康检查 ==========

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "rule_engine": self._rule_manager.health_check(),
            "alert_generator": self._alert_generator.health_check(),
            "compliance_checker": self._compliance_checker.health_check(),
            "limit_manager": self._limit_manager.health_check(),
            "operation_logger": self._operation_logger.health_check(),
            "risk_event_store": self._risk_event_store.health_check(),
            "realtime_monitor": (
                self._realtime_scanner.health_check() if self._realtime_scanner else {"status": "disabled"}
            ),
            "stats": {
                "total_rules": len(self._rule_manager.get_all_rules()),
                "total_risk_events": self._risk_event_store.count_events(),
                "total_operation_logs": self._operation_logger.count_logs(),
            },
        }

    # ========== 组件访问 ==========

    def get_rule_manager(self) -> RuleManager:
        """获取规则管理器"""
        return self._rule_manager

    def get_rule_executor(self) -> RuleExecutor:
        """获取规则执行器"""
        return self._rule_executor

    def get_alert_generator(self) -> AlertGenerator:
        """获取告警生成器"""
        return self._alert_generator

    def get_realtime_scanner(self) -> Optional[RealtimeRiskScanner]:
        """获取实时扫描器"""
        return self._realtime_scanner

    def get_compliance_checker(self) -> ComplianceChecker:
        """获取合规检查器"""
        return self._compliance_checker

    def get_limit_manager(self) -> LimitManager:
        """获取限额管理器"""
        return self._limit_manager

    def get_operation_logger(self) -> OperationLogger:
        """获取操作日志记录器"""
        return self._operation_logger

    def get_risk_event_store(self) -> RiskEventStore:
        """获取风险事件存储"""
        return self._risk_event_store

    def _load_default_rules(self) -> None:
        """加载默认预定义规则"""
        default_rules = get_default_pre_trade_rules()
        for rule in default_rules:
            self._rule_manager.add_rule(rule, created_by=0)  # 0 means system
        logger.info(f"Loaded {len(default_rules)} default pre-trade rules")
