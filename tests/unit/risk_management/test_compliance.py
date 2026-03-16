"""
Unit tests for compliance management
"""
import pytest
from datetime import datetime
from src.risk_management.rule_engine.rule_manager import RuleManager
from src.risk_management.rule_engine.rule_executor import RuleExecutor
from src.risk_management.compliance_management.compliance_checker import ComplianceChecker
from src.risk_management.compliance_management.abnormal_detector import AbnormalTradeDetector


def test_t1_restriction():
    """Test T+1 restriction check"""
    checker = ComplianceChecker(None)

    # Enough available after T+1 restriction
    result = checker.check_t1_restriction(
        available_quantity=1000,
        sell_quantity=500,
        today_bought=300,
    )
    # actually_available = 1000 - 300 = 700 >= 500
    assert result['passed'] is True

    # Not enough
    result = checker.check_t1_restriction(
        available_quantity=1000,
        sell_quantity=800,
        today_bought=300,
    )
    # actually_available = 700 < 800
    assert result['passed'] is False
    assert 'T+1限制' in result['message']


def test_price_limit_check():
    """Test price limit check"""
    checker = ComplianceChecker(None)

    # Price within limit
    result = checker.check_price_limit(10.5, 11.0, 9.0)
    assert result['passed'] is True

    # Above limit up
    result = checker.check_price_limit(11.5, 11.0, 9.0)
    assert result['passed'] is False
    assert '超过涨停价' in result['message']

    # Below limit down
    result = checker.check_price_limit(8.5, 11.0, 9.0)
    assert result['passed'] is False
    assert '低于跌停价' in result['message']


def test_lot_size_check():
    """Test lot size check (A-share 100 multiple requirement)"""
    checker = ComplianceChecker(None)

    # Valid
    result = checker.check_lot_size(1000)
    assert result['passed'] is True

    # Invalid
    result = checker.check_lot_size(150)
    assert result['passed'] is False
    assert '不是100的整数倍' in result['message']


def test_trading_hours_check():
    """Test trading hours check"""
    checker = ComplianceChecker(None)

    # Check on weekend should fail
    # Create a Saturday
    dt = datetime(2026, 3, 15)  # This is a Saturday
    result = checker.check_trading_hours(dt)
    assert result['passed'] is False
    assert result['is_trading_day'] is False

    # Check during trading hours on weekday
    dt = datetime(2026, 3, 13, 10, 0)  # Friday 10:00, trading hours
    result = checker.check_trading_hours(dt)
    assert result['passed'] is True
    assert result['is_trading_hours'] is True

    # Check before market open
    dt = datetime(2026, 3, 14, 8, 0)
    result = checker.check_trading_hours(dt)
    assert result['passed'] is False


def test_abnormal_large_order():
    """Test large order detection"""
    detector = AbnormalTradeDetector(large_order_threshold=1000000)

    trades = [
        {'trade_id': 1, 'price': 10, 'quantity': 50000},  # 500,000 < 1M
        {'trade_id': 2, 'price': 20, 'quantity': 100000},  # 2,000,000 > 1M
    ]

    anomalies = detector.detect_large_order(trades)
    assert len(anomalies) == 1
    assert anomalies[0]['trade_id'] == 2


def test_abnormal_frequent_trading():
    """Test frequent trading detection"""
    detector = AbnormalTradeDetector(frequent_daily_threshold=5)

    trades = []
    # 6 trades on same day
    for i in range(6):
        trades.append({
            'trade_id': i,
            'filled_time': datetime(2026, 3, 15, 9 + i, 0).isoformat(),
        })

    anomalies = detector.detect_frequent_trading(trades)
    assert len(anomalies) == 1
    assert anomalies[0]['count'] == 6
    assert anomalies[0]['threshold'] == 5


def test_abnormal_detect_all():
    """Test full detection"""
    detector = AbnormalTradeDetector()

    trades = [
        {'trade_id': 1, 'side': 'BUY', 'price': 10, 'quantity': 200000,
         'filled_time': datetime(2026, 3, 15, 10, 0).isoformat()},
        {'trade_id': 2, 'side': 'SELL', 'price': 10, 'quantity': 200000,
         'filled_time': datetime(2026, 3, 15, 10, 5).isoformat()},
    ]

    result = detector.detect_all(trades)
    assert 'total_anomalies' in result
    assert 'has_anomalies' in result
    # Large order threshold default 1M, 2M will be detected
    assert result['total_anomalies'] >= 2


def test_set_thresholds():
    """Test setting thresholds"""
    detector = AbnormalTradeDetector()
    detector.set_thresholds(
        large_order_threshold=2000000,
        frequent_daily_threshold=20,
        holding_days_threshold=2,
    )

    # Check thresholds updated
    trades = [{'trade_id': 1, 'price': 10, 'quantity': 150000}]  # 1.5M < 2M
    anomalies = detector.detect_large_order(trades)
    assert len(anomalies) == 0
