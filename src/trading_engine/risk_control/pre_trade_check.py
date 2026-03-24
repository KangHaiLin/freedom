"""
事前风控检查
下单前检查各种限制：资金充足性、持仓充足性、换手率限制、持仓集中度限制等
"""

from typing import Dict, Optional

from src.trading_engine.base.base_order import OrderSide
from src.trading_engine.position_management.portfolio_manager import PortfolioManager


class PreTradeCheckResult:
    """事前风控检查结果"""

    def __init__(self, passed: bool, message: str = "", details: Optional[Dict] = None):
        self.passed = passed
        self.message = message
        self.details = details or {}

    def __bool__(self):
        return self.passed


class PreTradeChecker:
    """事前风控检查器"""

    def __init__(
        self,
        max_position_value: float = 0.1,  # 单票最大市值占比
        max_daily_turnover: float = 0.25,  # 单日最大换手率
        max_concentration: int = 10,  # 最大持仓股票数量
        min_cash_reserve: float = 0.05,  # 最小现金保留比例
    ):
        """
        初始化事前风控
        Args:
            max_position_value: 单票最大市值占总资产比例 (0-1)
            max_daily_turnover: 单日最大换手率 (0-1)
            max_concentration: 最大持仓股票数量
            min_cash_reserve: 最小现金保留比例 (0-1)
        """
        self.max_position_value = max_position_value
        self.max_daily_turnover = max_daily_turnover
        self.max_concentration = max_concentration
        self.min_cash_reserve = min_cash_reserve

    def check_order(
        self,
        ts_code: str,
        side: OrderSide,
        quantity: int,
        price: float,
        portfolio: PortfolioManager,
        today_traded_value: float = 0.0,
    ) -> PreTradeCheckResult:
        """
        检查订单是否符合风控
        Args:
            ts_code: 股票代码
            side: 买卖方向
            quantity: 数量
            price: 价格
            portfolio: 投资组合
            today_traded_value: 今日已成交金额
        Returns:
            检查结果
        """
        total_asset = portfolio.get_total_asset()
        if total_asset <= 0:
            return PreTradeCheckResult(False, "总资产为零")

        # 检查最大持仓数量
        current_count = portfolio.get_position_count()
        if side == OrderSide.BUY:
            # 如果还没持仓，会增加计数
            if portfolio.get_position(ts_code) is None or portfolio.get_position(ts_code).is_empty():
                if current_count >= self.max_concentration:
                    return PreTradeCheckResult(
                        False, f"超出最大持仓数量限制: {current_count} >= {self.max_concentration}"
                    )

        # 检查单票市值限制
        order_value = quantity * price
        if side == OrderSide.BUY:
            # 买入后预估市值
            current_pos = portfolio.get_position(ts_code)
            current_mv = 0.0
            if current_pos is not None and current_pos.last_price is not None:
                current_mv = current_pos.quantity * current_pos.last_price
            expected_mv = current_mv + order_value
            max_allowed = total_asset * self.max_position_value
            if expected_mv > max_allowed:
                return PreTradeCheckResult(
                    False,
                    f"单票市值超出限制: {expected_mv:.2f} > {max_allowed:.2f} " f"({self.max_position_value*100:.1f}%)",
                )

        # 检查现金保留
        if side == OrderSide.BUY:
            required_cash = order_value * (1 + 0.001)  # 预留一点手续费
            available_cash = portfolio.get_cash()
            if available_cash - required_cash < total_asset * self.min_cash_reserve:
                return PreTradeCheckResult(
                    False,
                    f"现金不足，预留不足: 需要预留 {total_asset * self.min_cash_reserve:.2f}, "
                    f"剩余 {available_cash - required_cash:.2f}",
                )

        # 检查日换手率
        expected_turnover = (today_traded_value + order_value) / total_asset
        if expected_turnover > self.max_daily_turnover:
            return PreTradeCheckResult(
                False, f"单日换手率超出限制: {expected_turnover*100:.1f}% > {self.max_daily_turnover*100:.1f}%"
            )

        # 检查充足性
        if side == OrderSide.BUY:
            available_cash = portfolio.get_cash()
            required = order_value * (1 + 0.001)
            if available_cash < required:
                return PreTradeCheckResult(False, f"资金不足: 需要 {required:.2f}, 可用 {available_cash:.2f}")
        else:
            # 卖出，检查持仓足够
            pos = portfolio.get_position(ts_code)
            available = pos.quantity if pos is not None else 0
            if available < quantity:
                return PreTradeCheckResult(False, f"持仓不足: 需要 {quantity}, 可用 {available}")

        return PreTradeCheckResult(True, "通过")

    def check_max_position_count(self, current_count: int) -> PreTradeCheckResult:
        """检查持仓数量限制"""
        if current_count > self.max_concentration:
            return PreTradeCheckResult(False, f"超出最大持仓数量: {current_count} > {self.max_concentration}")
        return PreTradeCheckResult(True)
