"""
合规检查器
检查交易行为是否符合监管要求和A股规则
"""
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
import pandas as pd

from src.risk_management.rule_engine.rule_result import RuleResult
from src.risk_management.rule_engine.rule_executor import RuleExecutor


class ComplianceChecker:
    """
    合规检查器
    提供各类合规检查功能，确保交易符合监管要求
    """

    def __init__(self, rule_executor: RuleExecutor):
        self._rule_executor = rule_executor

    def check_pre_trade(
        self,
        user_id: int,
        ts_code: str,
        side: str,
        price: float,
        quantity: int,
        **kwargs,
    ) -> RuleResult:
        """
        交易前合规检查

        Args:
            user_id: 用户ID
            ts_code: 股票代码
            side: 买卖方向
            price: 价格
            quantity: 数量
            **kwargs: 额外上下文信息

        Returns:
            规则检查结果
        """
        context = {
            'user_id': user_id,
            'ts_code': ts_code,
            'side': side,
            'price': price,
            'quantity': quantity,
            **kwargs,
        }
        return self._rule_executor.execute('pre_trade', context, user_id)

    def check_t1_restriction(
        self,
        available_quantity: int,
        sell_quantity: int,
        today_bought: int,
    ) -> Dict[str, Any]:
        """
        检查A股T+1限制

        Args:
            available_quantity: 总可用持仓
            sell_quantity: 卖出数量
            today_bought: 今日买入数量

        Returns:
            检查结果，包含是否通过和可卖出数量
        """
        # A股T+1: 今日买入不能今日卖出
        actually_available = available_quantity - today_bought
        if actually_available >= sell_quantity:
            return {
                'passed': True,
                'available': actually_available,
                'requested': sell_quantity,
                'message': '',
            }
        else:
            return {
                'passed': False,
                'available': actually_available,
                'requested': sell_quantity,
                'message': f'T+1限制，今日买入{today_bought}股不可卖出，实际可用{actually_available}股',
            }

    def check_price_limit(
        self,
        price: float,
        limit_up: float,
        limit_down: float,
    ) -> Dict[str, Any]:
        """
        检查价格是否在涨跌停范围内

        Args:
            price: 委托价格
            limit_up: 涨停价
            limit_down: 跌停价

        Returns:
            检查结果
        """
        if price > limit_up:
            return {
                'passed': False,
                'message': f'委托价格{price}超过涨停价{limit_up}',
                'price': price,
                'limit_up': limit_up,
                'limit_down': limit_down,
            }
        if price < limit_down:
            return {
                'passed': False,
                'message': f'委托价格{price}低于跌停价{limit_down}',
                'price': price,
                'limit_up': limit_up,
                'limit_down': limit_down,
            }
        return {
            'passed': True,
            'message': '',
            'price': price,
            'limit_up': limit_up,
            'limit_down': limit_down,
        }

    def check_lot_size(
        self,
        quantity: int,
        min_lot: int = 100,
    ) -> Dict[str, Any]:
        """
        检查买入数量是否是整手（A股要求买入必须是100股整数倍）

        Args:
            quantity: 买入数量
            min_lot: 每手股数，默认100

        Returns:
            检查结果
        """
        if quantity % min_lot != 0:
            return {
                'passed': False,
                'message': f'买入数量{quantity}不是{min_lot}的整数倍',
                'quantity': quantity,
                'min_lot': min_lot,
            }
        return {
            'passed': True,
            'message': '',
        }

    def check_trading_hours(
        self,
        dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        检查是否在交易时段内

        Args:
            dt: 指定时间，默认当前时间

        Returns:
            检查结果
        """
        dt = dt or datetime.now()
        weekday = dt.weekday()
        if weekday >= 5:  # 周六日
            return {
                'passed': False,
                'message': '非交易日',
                'is_trading_day': False,
            }

        hour = dt.hour
        minute = dt.minute
        current_time = hour * 60 + minute

        # 早盘集合竞价 9:15-9:25 允许
        # 连续竞价 9:30-11:30
        # 午盘 13:00-15:00
        in_trading = (
            (555 <= current_time <= 690) or  # 9:15-11:30
            (780 <= current_time <= 900)     # 13:00-15:00
        )

        if not in_trading:
            return {
                'passed': False,
                'message': '非交易时段',
                'is_trading_hours': False,
            }

        return {
            'passed': True,
            'message': '',
            'is_trading_day': True,
            'is_trading_hours': True,
        }

    def check_daily_position_limit(
        self,
        current_net_buy: float,
        limit: float,
    ) -> Dict[str, Any]:
        """
        检查单日净买入限额

        Args:
            current_net_buy: 当前净买入金额
            limit: 限额

        Returns:
            检查结果
        """
        if current_net_buy > limit:
            return {
                'passed': False,
                'message': f'单日净买入{current_net_buy:.2f}超过限额{limit:.2f}',
                'current': current_net_buy,
                'limit': limit,
            }
        return {
            'passed': True,
            'message': '',
            'current': current_net_buy,
            'limit': limit,
        }

    def get_compliance_summary(
        self,
        start_date: date,
        end_date: date,
        trades: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        获取时间段合规检查汇总

        Args:
            start_date: 开始日期
            end_date: 结束日期
            trades: 交易记录列表

        Returns:
            合规汇总数据
        """
        df = pd.DataFrame(trades)
        if df.empty:
            return {
                'total_trades': 0,
                'violations': 0,
                'compliance_rate': 1.0,
            }

        # 统计违规情况
        # 需要实际执行规则检查
        total = len(df)
        violations = 0
        violation_details = []

        for _, trade in df.iterrows():
            context = trade.to_dict()
            result = self._rule_executor.execute('compliance', context)
            if not result.passed():
                violations += 1
                violation_details.append({
                    'trade_id': trade.get('trade_id'),
                    'violations': [v.to_dict() for v in result.get_violations()],
                })

        return {
            'total_trades': total,
            'violations': violations,
            'compliance_rate': (total - violations) / total if total > 0 else 1.0,
            'violation_details': violation_details,
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'ok',
        }
