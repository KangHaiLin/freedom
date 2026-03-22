"""
Unit tests for interface.py
"""

import pytest

from src.trading_engine.broker_adapter.interface import CommissionCalculator, CommissionConfig


def test_commission_calculator_buy():
    """测试买入佣金计算"""
    calc = CommissionCalculator()
    # 买入1000股，价格10元
    # 佣金 = 1000*10 * 0.0003 = 3元，但最低5元
    # 印花税买入不收，过户费 10000 * 0.00002 = 0.2
    # 总计 5 + 0.2 = 5.2
    commission = calc.calculate_buy_commission(1000, 10.0)
    assert abs(commission - 5.2) < 0.01


def test_commission_calculator_sell():
    """测试卖出佣金计算"""
    calc = CommissionCalculator()
    # 卖出1000股，价格10元
    # 佣金最低5元，印花税 10000 * 0.001 = 10元，过户费0.2元
    # 总计 5 + 10 + 0.2 = 15.2
    commission = calc.calculate_sell_commission(1000, 10.0)
    assert abs(commission - 15.2) < 0.01


def test_custom_config():
    """测试自定义配置"""
    config = CommissionConfig(
        commission_rate=0.0005,
        min_commission=5.0,
        stamp_duty_rate=0.001,
        transfer_fee_rate=0.00002,
    )
    calc = CommissionCalculator(config)
    commission = calc.calculate_buy_commission(1000, 10.0)
    # 1000*10 * 0.0005 = 5，正好满足最低，加上过户费 0.2
    assert abs(commission - 5.2) < 0.01


def test_zero_commission():
    """测试零佣金"""
    config = CommissionConfig(
        commission_rate=0.0,
        min_commission=0.0,
    )
    calc = CommissionCalculator(config)
    commission = calc.calculate_buy_commission(1000, 10.0)
    # 只有过户费
    assert abs(commission - 0.2) < 0.01
