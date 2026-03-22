"""
Unit tests for position_calculator.py
"""

import pytest

from src.trading_engine.position_management.position import Position
from src.trading_engine.position_management.position_calculator import PositionCalculator


def create_test_positions():
    """创建测试持仓"""
    positions = {}
    # 持仓1: 1000股，成本10，价格12
    pos1 = Position("000001.SZ", 1000, 10.0)
    pos1.update_price(12.0)
    positions["000001.SZ"] = pos1
    # 持仓2: 500股，成本20，价格18
    pos2 = Position("000002.SZ", 500, 20.0)
    pos2.update_price(18.0)
    positions["000002.SZ"] = pos2
    # 空持仓
    positions["000003.SZ"] = Position("000003.SZ", 0, 0.0)
    return positions


def test_calculate_total_market_value():
    """测试计算总市值"""
    positions = create_test_positions()
    # 000001: 1000 * 12 = 12000
    # 000002: 500 * 18 = 9000
    # 总计: 21000
    total = PositionCalculator.calculate_total_market_value(positions)
    assert abs(total - 21000) < 0.01


def test_calculate_total_cost():
    """测试计算总成本"""
    positions = create_test_positions()
    # 000001: 1000 * 10 = 10000
    # 000002: 500 * 20 = 10000
    # 总计: 20000
    total = PositionCalculator.calculate_total_cost(positions)
    assert abs(total - 20000) < 0.01


def test_calculate_total_unrealized_pnl():
    """测试计算总未实现盈亏"""
    positions = create_test_positions()
    # 000001: (12-10)*1000 = 2000
    # 000002: (18-20)*500 = -1000
    # 总计: 1000
    total = PositionCalculator.calculate_total_unrealized_pnl(positions)
    assert abs(total - 1000) < 0.01


def test_calculate_weights():
    """测试计算权重"""
    positions = create_test_positions()
    weights = PositionCalculator.calculate_weights(positions)
    # 000001: 12000/21000 ≈ 0.5714
    # 000002: 9000/21000 ≈ 0.4286
    assert abs(weights["000001.SZ"] - 0.5714) < 0.001
    assert abs(weights["000002.SZ"] - 0.4286) < 0.001
    assert weights["000003.SZ"] == 0.0


def test_get_non_empty_positions():
    """测试获取非空持仓"""
    positions = create_test_positions()
    non_empty = PositionCalculator.get_non_empty_positions(positions)
    assert len(non_empty) == 2


def test_calculate_position_count():
    """测试计算持仓数量"""
    positions = create_test_positions()
    count = PositionCalculator.calculate_position_count(positions)
    assert count == 2


def test_calculate_portfolio_pnl_percentage():
    """测试计算投资组合收益率"""
    positions = create_test_positions()
    # 总成本 20000，现金 0，总盈亏 1000
    # 收益率 = 1000 / 20000 = 0.05 = 5%
    pct = PositionCalculator.calculate_portfolio_pnl_percentage(positions, 0.0)
    assert abs(pct - 0.05) < 0.001


def test_calculate_portfolio_summary():
    """测试计算投资组合汇总"""
    positions = create_test_positions()
    summary = PositionCalculator.calculate_portfolio_summary(positions, 5000.0)
    assert summary["position_count"] == 2
    assert abs(summary["total_market_value"] - 21000) < 0.01
    assert abs(summary["total_cost"] - 20000) < 0.01
    assert summary["cash"] == 5000
    assert abs(summary["total_asset"] - 26000) < 0.01
    assert abs(summary["total_unrealized_pnl"] - 1000) < 0.01
    # 收益率 1000 / (20000 + 5000) = 0.04 = 4%
    assert abs(summary["pnl_percentage"] - 4.0) < 0.01
