"""
Unit tests for audit trail
"""
import pytest
import tempfile
from datetime import datetime, date
from src.risk_management.audit_trail.operation_logger import OperationLogger, OperationType
from src.risk_management.audit_trail.risk_event_store import RiskEventStore


def test_operation_logger_log():
    """Test logging operation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = OperationLogger(log_file_path=f"{tmpdir}/test.log", enable_console=False)

        log_id = logger.log(
            operation_type=OperationType.RULE_CREATE,
            operator_id=1,
            details={'rule_id': 'test-001'},
        )

        assert log_id == 1
        assert logger.count_logs() == 1

        logs = logger.get_recent_logs(10)
        assert len(logs) == 1
        assert logs[0].operation_type == OperationType.RULE_CREATE
        assert logs[0].operator_id == 1


def test_operation_logger_query():
    """Test querying logs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = OperationLogger(log_file_path=f"{tmpdir}/test.log", enable_console=False)

        logger.log(OperationType.RULE_CREATE, 1, {'rule_id': 'r1'})
        logger.log(OperationType.RULE_CREATE, 1, {'rule_id': 'r2'})
        logger.log(OperationType.RULE_DELETE, 1, {'rule_id': 'r1'})

        logs = logger.query_logs(operation_type=OperationType.RULE_CREATE)
        assert len(logs) == 2

        logs = logger.query_logs(operation_type=OperationType.RULE_DELETE)
        assert len(logs) == 1


def test_operation_logger_json_serialization():
    """Test JSON serialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = OperationLogger(log_file_path=f"{tmpdir}/test.log", enable_console=False)

        logger.log(
            operation_type=OperationType.RISK_ALERT,
            operator_id=1,
            details={'alert_level': 'warning', 'message': 'test'},
        )

        assert logger.count_logs() == 1
        # Create new logger to test loading
        logger2 = OperationLogger(log_file_path=f"{tmpdir}/test.log", enable_console=False)
        assert logger2.count_logs() == 1


def test_risk_event_add():
    """Test adding risk event"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = RiskEventStore(storage_path=f"{tmpdir}/events.jsonl")

        event_id = store.add_event(
            event_type='pre_trade',
            event_level='error',
            message='Test error',
            rule_id='test-001',
            user_id=1,
            ts_code='000001.SZ',
            details={'current': 150, 'limit': 100},
        )

        assert event_id == 1
        assert store.count_events() == 1

        event = store.get_event(1)
        assert event is not None
        assert event.message == 'Test error'
        assert event.rule_id == 'test-001'
        assert event.details['current'] == 150


def test_risk_event_mark_handled():
    """Test marking event as handled"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = RiskEventStore(storage_path=f"{tmpdir}/events.jsonl")

        event_id = store.add_event(
            event_type='pre_trade',
            event_level='warning',
            message='Test',
        )

        assert store.get_event(event_id).handled is False

        result = store.mark_handled(event_id, 1, 'Handled this event')
        assert result is True
        assert store.get_event(event_id).handled is True
        assert store.get_event(event_id).handled_note == 'Handled this event'


def test_risk_event_query():
    """Test querying events"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = RiskEventStore(storage_path=f"{tmpdir}/events.jsonl")

        store.add_event('pre_trade', 'error', 'error 1', rule_id='r1', user_id=1)
        store.add_event('pre_trade', 'warning', 'warn 1', rule_id='r1', user_id=1)
        store.add_event('position', 'warning', 'warn 2', rule_id='r2', user_id=2)

        events = store.query_events(event_type='pre_trade')
        assert len(events) == 2

        events = store.query_events(event_level='error')
        assert len(events) == 1

        events = store.query_events(user_id=1)
        assert len(events) == 2

        events = store.query_events(handled=False)
        assert len(events) == 3


def test_risk_event_statistics():
    """Test getting statistics"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = RiskEventStore(storage_path=f"{tmpdir}/events.jsonl")

        store.add_event('pre_trade', 'error', 'error 1')
        store.add_event('pre_trade', 'warning', 'warn 1')
        store.add_event('position', 'warning', 'warn 2')

        stats = store.get_statistics()
        assert stats['total_events'] == 3
        assert stats['by_level']['error'] == 1
        assert stats['by_level']['warning'] == 2
        assert stats['by_type']['pre_trade'] == 2
        assert stats['unhandled'] == 3


def test_health_check():
    """Test health check"""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = OperationLogger(log_file_path=f"{tmpdir}/test.log")
        store = RiskEventStore(storage_path=f"{tmpdir}/events.jsonl")

        health_logger = logger.health_check()
        assert health_logger['status'] == 'ok'

        health_store = store.health_check()
        assert health_store['status'] == 'ok'
        assert health_store['file_exists'] is True
