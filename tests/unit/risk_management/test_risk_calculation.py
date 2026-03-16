"""
Unit tests for risk calculation
"""
import pytest
import numpy as np
import pandas as pd
from src.risk_management.risk_calculation.var_calculator import VaRCalculator
from src.risk_management.risk_calculation.stress_tester import StressTester
from src.risk_management.risk_calculation.scenario_analyzer import ScenarioAnalyzer
from src.risk_management.risk_calculation.limit_manager import LimitManager, LimitType, RiskLimit


# ========== VaR tests ==========

def test_parametric_var():
    """Test parametric VaR calculation"""
    # Generate normal returns
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 1000))

    calculator = VaRCalculator(confidence_level=0.95, holding_days=1)
    result = calculator.parametric_var(returns, 100000.0)

    assert result['method'] == 'parametric'
    assert result['var'] > 0
    assert result['expected_shortfall'] > result['var']
    assert 1000 < result['var'] < 3000  # Reasonable range for 100k portfolio 1% daily vol


def test_historical_var():
    """Test historical simulation VaR"""
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 1000))

    calculator = VaRCalculator(confidence_level=0.95, holding_days=1)
    result = calculator.historical_simulation(returns, 100000.0)

    assert result['method'] == 'historical'
    assert result['var'] > 0
    assert result['sample_size'] == 1000


def test_monte_carlo_var():
    """Test Monte Carlo VaR"""
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 1000))

    calculator = VaRCalculator(confidence_level=0.95, holding_days=1)
    result = calculator.monte_carlo_simulation(returns, 100000.0, simulations=1000, seed=42)

    assert result['method'] == 'monte_carlo'
    assert result['var'] > 0
    assert result['simulations'] == 1000


def test_var_consistency():
    """All methods should give roughly similar results for normal distribution"""
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 1000))
    portfolio_value = 100000.0

    calc = VaRCalculator(confidence_level=0.95, holding_days=1)
    res_param = calc.parametric_var(returns, portfolio_value)
    res_hist = calc.historical_simulation(returns, portfolio_value)

    # Should be within 20% of each other
    diff = abs(res_param['var'] - res_hist['var']) / res_param['var']
    assert diff < 0.3


# ========== Stress test tests ==========

def test_stress_tester_standard_scenarios():
    """Test that standard scenarios are loaded"""
    tester = StressTester()
    scenarios = tester.list_scenarios()

    assert len(scenarios) >= 4
    ids = [s['id'] for s in scenarios]
    assert 'systemic_down_10' in ids
    assert 'systemic_down_20' in ids


def test_stress_test_run():
    """Test running stress test"""
    tester = StressTester()

    positions = {
        '000001.SZ': {'quantity': 1000, 'last_price': 10.0},
        '600000.SH': {'quantity': 500, 'last_price': 20.0},
    }

    result = tester.run_stress_test('systemic_down_10', positions)

    assert result['success'] is True
    assert result['total_pnl'] < 0  # Should lose money
    assert result['total_pnl_pct'] == pytest.approx(-10, abs=1)  # ~-10%
    assert len(result['position_results']) == 2


def test_stress_test_custom_shocks():
    """Test custom shocks"""
    tester = StressTester()

    positions = {
        '000001.SZ': {'quantity': 1000, 'last_price': 10.0},
    }

    result = tester.run_stress_test(
        'systemic_down_10',
        positions,
        custom_shocks={'000001.SZ': -0.20}
    )

    assert result['success'] is True
    # 1000 * 10 * (-0.20) = -2000
    assert result['total_pnl'] == pytest.approx(-2000)


# ========== Scenario analysis tests ==========

def test_scenario_analyzer_standard_scenarios():
    """Test standard scenarios"""
    analyzer = ScenarioAnalyzer()
    scenarios = analyzer.list_scenarios()

    assert len(scenarios) >= 4
    assert any(s['id'] == 'rate_up_100bp' for s in scenarios)


def test_scenario_analysis():
    """Test scenario analysis"""
    analyzer = ScenarioAnalyzer()

    exposures = {
        'interest_rate': 100000,
        'real_estate_index': 50000,
    }

    result = analyzer.analyze('rate_up_100bp', exposures, 200000.0)

    assert result['success'] is True
    # Real estate should drop when rates rise
    assert result['total_pnl'] < 0


# ========== Limit manager tests ==========

def test_add_limit():
    """Test adding limit"""
    manager = LimitManager()
    limit_id = manager.add_limit(RiskLimit(
        limit_id=0,
        limit_type=LimitType.SINGLE_POSITION_RATIO,
        limit_value=0.3,
        description='Single position limit',
    ))

    assert limit_id > 0
    assert manager.get_limit(limit_id) is not None


def test_check_limit():
    """Test limit checking"""
    manager = LimitManager()
    manager.add_limit(RiskLimit(
        limit_id=0,
        limit_type=LimitType.USER_DAILY_AMOUNT,
        limit_value=1000000,
    ))

    result = manager.check_limit(LimitType.USER_DAILY_AMOUNT, 500000)
    assert result['passed'] is True

    result = manager.check_limit(LimitType.USER_DAILY_AMOUNT, 1500000)
    assert result['passed'] is False
    assert '超出' in result['message']


def test_daily_amount_check():
    """Test daily amount accumulation"""
    manager = LimitManager()
    manager.set_default_limits(user_daily_amount=1000000)

    result = manager.check_daily_amount(1, 200000, 1000000)
    assert result['passed'] is True

    result = manager.check_daily_amount(1, 300000, 1000000)
    assert result['passed'] is True
    assert manager.get_daily_usage(LimitType.USER_DAILY_AMOUNT, 1) == 500000

    result = manager.check_daily_amount(1, 600000, 1000000)
    assert result['passed'] is False


def test_reset_daily():
    """Test reset daily usage"""
    manager = LimitManager()
    manager.set_default_limits(user_daily_amount=1000000)
    manager.check_daily_amount(1, 500000, 1000000)
    assert manager.get_daily_usage(LimitType.USER_DAILY_AMOUNT, 1) == 500000

    manager.reset_daily_usage()
    assert manager.get_daily_usage(LimitType.USER_DAILY_AMOUNT, 1) == 0


def test_default_limits():
    """Test setting default limits"""
    manager = LimitManager()
    manager.set_default_limits()

    stats = manager.health_check()
    assert stats['total_limits'] == 4
    assert stats['status'] == 'ok'
