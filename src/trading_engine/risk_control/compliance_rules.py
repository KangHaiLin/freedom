"""
A股合规规则检查
- T+1 交易限制：当日买入不能当日卖出
- 涨跌停价格限制：不能超过涨跌停价格下单
- 退市股票禁止买入
- 停牌股票禁止交易
"""
from typing import Dict, Tuple, Optional, List
from datetime import datetime, date

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.position_management.position import Position
from src.trading_engine.position_management.portfolio_manager import PortfolioManager


class ComplianceCheckResult:
    """合规检查结果"""

    def __init__(self, compliant: bool, message: str = ""):
        self.compliant = compliant
        self.message = message

    def __bool__(self):
        return self.compliant


class AShareComplianceRules:
    """
    A股交易合规规则检查
    遵循中国证监会和交易所规则
    """

    def __init__(
        self,
        enable_t1_check: bool = True,
        enable_price_limit_check: bool = True,
    ):
        """
        初始化合规规则
        Args:
            enable_t1_check: 是否启用T+1检查
            enable_price_limit_check: 是否启用涨跌停价格检查
        """
        self.enable_t1_check = enable_t1_check
        self.enable_price_limit_check = enable_price_limit_check

    def check_order(
        self,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        price: Optional[float],
        portfolio: PortfolioManager,
        today_trades: Optional[List[Dict]] = None,
        limit_up: Optional[float] = None,
        limit_down: Optional[float] = None,
        is_suspended: bool = False,
        is_delisted: bool = False,
    ) -> ComplianceCheckResult:
        """
        综合检查订单合规性
        Args:
            ts_code: 股票代码
            side: 买卖方向
            quantity: 数量
            price: 价格
            portfolio: 投资组合
            today_trades: 今日交易记录
            limit_up: 涨停价，None表示未知
            limit_down: 跌停价，None表示未知
            is_suspended: 是否停牌
            is_delisted: 是否退市
        Returns:
            检查结果
        """

        # 检查退市
        if is_delisted:
            if side == OrderSide.BUY:
                return ComplianceCheckResult(False, f"禁止买入退市股票: {ts_code}")

        # 检查停牌
        if is_suspended:
            return ComplianceCheckResult(False, f"禁止交易停牌股票: {ts_code}")

        # 检查T+1
        if self.enable_t1_check and side == OrderSide.SELL:
            if not self.check_t1_allowed(ts_code, quantity, portfolio, today_trades):
                return ComplianceCheckResult(
                    False,
                    f"T+1限制: 当日买入不能当日卖出，{ts_code} 可用不足"
                )

        # 检查涨跌停
        if self.enable_price_limit_check and price is not None:
            ok, msg = self.check_price_limit(price, limit_up, limit_down)
            if not ok:
                return ComplianceCheckResult(False, msg)

        return ComplianceCheckResult(True, "合规")

    def check_t1_allowed(
        self,
        ts_code: str,
        sell_quantity: int,
        portfolio: PortfolioManager,
        today_trades: Optional[List[Dict]] = None,
    ) -> bool:
        """
        检查T+1卖出是否允许
        Args:
            ts_code: 股票代码
            sell_quantity: 卖出数量
            portfolio: 投资组合
            today_trades: 今日买入记录
        Returns:
            是否允许卖出
        """
        if not self.enable_t1_check:
            return True

        # 获取昨日之前持仓数量
        position = portfolio.get_position(ts_code)
        if position is None:
            return sell_quantity == 0

        prev_available = position.quantity
        if today_trades:
            # 减去今日买入的
            for trade in today_trades:
                if trade.get('ts_code') == ts_code and trade.get('side') == OrderSide.BUY:
                    prev_available -= trade.get('filled_quantity', 0)

        # 昨日之前的持仓足够卖出就允许
        return prev_available >= sell_quantity

    @staticmethod
    def check_price_limit(
        price: float,
        limit_up: Optional[float],
        limit_down: Optional[float],
    ) -> Tuple[bool, str]:
        """
        检查价格是否在涨跌停范围内
        Args:
            price: 委托价格
            limit_up: 涨停价
            limit_down: 跌停价
        Returns:
            (是否合法, 消息)
        """
        if limit_up is None or limit_down is None:
            return True, ""

        if price > limit_up:
            return False, f"价格超出涨停限制: {price:.2f} > {limit_up:.2f}"

        if price < limit_down:
            return False, f"价格超出跌停限制: {price:.2f} < {limit_down:.2f}"

        return True, ""

    @staticmethod
    def calculate_limit_price(pre_close: float, limit_rate: float = 0.10) -> Tuple[float, float]:
        """
        计算涨跌停价格
        Args:
            pre_close: 昨日收盘价
            limit_rate: 涨跌幅限制，默认10%
        Returns:
            (limit_up, limit_down)
        """
        limit_up = round(pre_close * (1 + limit_rate), 2)
        limit_down = round(pre_close * (1 - limit_rate), 2)
        return limit_up, limit_down

    @staticmethod
    def get_limit_rate(ts_code: str) -> float:
        """
        根据股票代码获取涨跌停比例
        Args:
            ts_code: 股票代码
        Returns:
            涨跌幅限制比例
        """
        # ST/*ST 5%
        if ts_code.startswith('ST') or ts_code.startswith('*ST') or 'ST' in ts_code:
            return 0.05
        # 科创板/创业板注册制新股上市前5日不设限，这里简化处理，默认还是10%
        # 实际应该根据具体板块判断
        return 0.10
