"""
Unit tests for report_generator.py
"""

import json
import os
import tempfile
from datetime import date

import pytest

from src.strategy_research.base import BacktestResult, DailyStats
from src.strategy_research.report_generator.report_generator import (
    generate_json_report,
    generate_text_report,
    generate_html_report,
    save_report,
)


def create_test_backtest_result() -> BacktestResult:
    """Create a test backtest result for testing"""
    daily_stats = [
        DailyStats(
            date=date(2024, 1, 1),
            total_assets=100000.0,
            cash=100000.0,
            market_value=0.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            turnover=0.0,
            trades=0,
        ),
        DailyStats(
            date=date(2024, 1, 2),
            total_assets=101000.0,
            cash=90000.0,
            market_value=11000.0,
            daily_pnl=1000.0,
            daily_pnl_pct=0.01,
            turnover=0.1,
            trades=1,
        ),
        DailyStats(
            date=date(2024, 1, 3),
            total_assets=102500.0,
            cash=88500.0,
            market_value=14000.0,
            daily_pnl=1500.0,
            daily_pnl_pct=0.015,
            turnover=0.14,
            trades=1,
        ),
    ]

    return BacktestResult(
        strategy_name="TestStrategy",
        initial_capital=100000.0,
        final_capital=102500.0,
        total_pnl=2500.0,
        total_pnl_pct=2.5,
        annualized_return=15.2,
        sharpe_ratio=1.8,
        max_drawdown=3.2,
        max_drawdown_date=None,
        win_rate=65.0,
        profit_loss_ratio=1.5,
        total_trades=100,
        winning_trades=65,
        losing_trades=35,
        avg_holding_days=5.2,
        turnover_rate=120.5,
        daily_stats=daily_stats,
        trades=[],
        positions=[],
        extra_info={},
    )


def test_generate_json_report():
    """Test generating JSON report"""
    result = create_test_backtest_result()
    json_str = generate_json_report(result)

    # Parse back and verify
    data = json.loads(json_str)
    assert data["strategy_name"] == "TestStrategy"
    assert data["initial_capital"] == 100000.0
    assert data["final_capital"] == 102500.0
    assert data["total_pnl_pct"] == 2.5
    assert len(data["daily_stats"]) == 3


def test_generate_text_report():
    """Test generating text report"""
    result = create_test_backtest_result()
    text = generate_text_report(result)

    assert "回测报告: TestStrategy" in text
    assert "初始资金: 100000.00" in text
    assert "最终资金: 102500.00" in text
    assert "总收益: 2.50%" in text
    assert "年化收益: 15.20%" in text
    assert "夏普比率: 1.80" in text
    assert "最大回撤: 3.20%" in text
    assert "胜率: 65.0%" in text
    assert "盈亏比: 1.50" in text
    assert "总交易次数: 100" in text
    assert "生成时间:" in text


def test_generate_html_report():
    """Test generating HTML report"""
    result = create_test_backtest_result()
    html = generate_html_report(result)

    assert "<title>回测报告 - TestStrategy</title>" in html
    assert "TestStrategy" in html
    assert "初始资金" in html
    assert "100000.00" in html
    assert "权益曲线" in html
    assert "chart.js" in html
    assert "new Chart" in html


def test_generate_html_report_no_charts():
    """Test generating HTML report without charts"""
    result = create_test_backtest_result()
    html = generate_html_report(result, include_charts=False)

    assert "<title>回测报告 - TestStrategy</title>" in html
    assert "权益曲线" not in html
    assert "Chart.js" not in html


def test_save_report_html():
    """Test saving HTML report to file"""
    result = create_test_backtest_result()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        temp_path = f.name

    try:
        result_dict = save_report(result, temp_path, format="html")
        assert result_dict["success"] is True
        assert result_dict["format"] == "html"
        assert result_dict["content_type"] == "text/html"

        # Verify file was written
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_json():
    """Test saving JSON report to file"""
    result = create_test_backtest_result()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        result_dict = save_report(result, temp_path, format="json")
        assert result_dict["success"] is True
        assert result_dict["format"] == "json"
        assert result_dict["content_type"] == "application/json"

        # Verify file contains valid JSON
        with open(temp_path, 'r') as f:
            data = json.load(f)
        assert data["strategy_name"] == "TestStrategy"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_text():
    """Test saving text report to file"""
    result = create_test_backtest_result()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        temp_path = f.name

    try:
        result_dict = save_report(result, temp_path, format="text")
        assert result_dict["success"] is True
        assert result_dict["format"] == "text"
        assert result_dict["content_type"] == "text/plain"

        with open(temp_path, 'r') as f:
            content = f.read()
        assert "回测报告: TestStrategy" in content
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_report_unknown_format():
    """Test saving with unknown format returns error"""
    result = create_test_backtest_result()
    result_dict = save_report(result, "/tmp/test", format="pdf")

    assert result_dict["success"] is False
    assert "Unknown format" in result_dict["error"]


def test_save_report_io_error():
    """Test IO error when saving to invalid path"""
    result = create_test_backtest_result()
    # Try to write to a directory that doesn't exist
    result_dict = save_report(result, "/nonexistent/path/report.html", format="html")

    assert result_dict["success"] is False
    assert "error" in result_dict
