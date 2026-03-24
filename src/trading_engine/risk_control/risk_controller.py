"""
风险控制器
整合事前风控和合规检查，统一接口
"""

from typing import Any, Dict, List, Optional

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.position_management.portfolio_manager import PortfolioManager
from src.trading_engine.risk_control.compliance_rules import AShareComplianceRules
from src.trading_engine.risk_control.pre_trade_check import PreTradeChecker


class RiskCheckResult:
    """综合风控检查结果"""

    def __init__(
        self,
        passed: bool,
        pre_trade_passed: Optional[bool] = None,
        compliance_passed: Optional[bool] = None,
        message: str = "",
        details: Optional[Dict] = None,
    ):
        self.passed = passed
        self.pre_trade_passed = pre_trade_passed
        self.compliance_passed = compliance_passed
        self.message = message
        self.details = details or {}

    def __bool__(self):
        return self.passed


class RiskController:
    """
    统一风险控制器
    整合事前风控和合规规则检查
    """

    def __init__(
        self,
        pre_trade_checker: Optional[PreTradeChecker] = None,
        compliance_rules: Optional[AShareComplianceRules] = None,
    ):
        """
        初始化风险控制器
        Args:
            pre_trade_checker: 事前风控检查器，None使用默认
            compliance_rules: 合规规则，None使用默认A股规则
        """
        self._pre_trade = pre_trade_checker or PreTradeChecker()
        self._compliance = compliance_rules or AShareComplianceRules()

    def check_order(
        self,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        price: Optional[float],
        portfolio: PortfolioManager,
        today_traded_value: float = 0.0,
        today_trades: Optional[List[Dict]] = None,
        limit_up: Optional[float] = None,
        limit_down: Optional[float] = None,
        is_suspended: bool = False,
        is_delisted: bool = False,
    ) -> RiskCheckResult:
        """
        综合风控检查
        Args:
            ts_code: 股票代码
            side: 买卖方向
            quantity: 数量
            price: 价格
            portfolio: 投资组合
            today_traded_value: 今日已成交金额
            today_trades: 今日交易记录（用于T+1检查）
            limit_up: 涨停价
            limit_down: 跌停价
            is_suspended: 是否停牌
            is_delisted: 是否退市
        Returns:
            风控结果
        """
        # 先事前风控
        pre_result = self._pre_trade.check_order(
            ts_code=ts_code,
            side=side,
            quantity=quantity,
            price=price if price else 0,
            portfolio=portfolio,
            today_traded_value=today_traded_value,
        )
        if not pre_result.passed:
            return RiskCheckResult(
                passed=False,
                pre_trade_passed=False,
                compliance_passed=None,
                message=pre_result.message,
                details=pre_result.details,
            )

        # 再合规检查
        comp_result = self._compliance.check_order(
            ts_code=ts_code,
            side=side,
            quantity=quantity,
            price=price,
            portfolio=portfolio,
            today_trades=today_trades,
            limit_up=limit_up,
            limit_down=limit_down,
            is_suspended=is_suspended,
            is_delisted=is_delisted,
        )
        if not comp_result.compliant:
            return RiskCheckResult(
                passed=False,
                pre_trade_passed=True,
                compliance_passed=False,
                message=comp_result.message,
            )

        return RiskCheckResult(
            passed=True,
            pre_trade_passed=True,
            compliance_passed=True,
            message="风控检查通过",
        )

    def check_portfolio_risk(
        self,
        portfolio: PortfolioManager,
        max_drawdown: float = 0.2,
    ) -> Dict[str, Any]:
        """
        检查投资组合整体风险
        Args:
            portfolio: 投资组合
            max_drawdown: 最大允许回撤
        Returns:
            检查结果
        """
        summary = portfolio.get_summary()
        total_asset = summary.get("total_asset", 0.0)
        initial_cash = portfolio.get_initial_cash()

        # 计算累计收益
        if initial_cash <= 0:
            return {
                "alert": False,
                "message": "初始资金为零",
                "current_drawdown": 0.0,
            }

        total_pnl = summary.get("total_pnl", 0.0)
        current_assets = total_asset
        if current_assets < initial_cash:
            current_drawdown = (initial_cash - current_assets) / initial_cash
        else:
            current_drawdown = 0.0

        alert = current_drawdown > max_drawdown

        return {
            "alert": alert,
            "current_drawdown": current_drawdown,
            "max_drawdown_limit": max_drawdown,
            "total_asset": total_asset,
            "total_pnl": total_pnl,
            "message": (
                f"当前回撤 {current_drawdown*100:.1f}%，限制 {max_drawdown*100:.1f}%"
                if not alert
                else f"回撤超出限制: {current_drawdown*100:.1f}% > {max_drawdown*100:.1f}%"
            ),
        }

    def get_pre_trade_checker(self) -> PreTradeChecker:
        """获取事前风控检查器"""
        return self._pre_trade

    def get_compliance_rules(self) -> AShareComplianceRules:
        """获取合规规则"""
        return self._compliance

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "pre_trade_enabled": True,
            "compliance_enabled": True,
        }
