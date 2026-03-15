"""
Unit tests for trade_statistics.py
"""
import pytest
from datetime import datetime
from src.trading_engine.trade_record.trade_statistics import TradeStatistics
from src.trading_engine.trade_record.trade_record import TradeRecord
from src.trading_engine.base.base_order import OrderSide


def create_test_trades():
    """创建测试交易数据"""
    dt = datetime.now()
    trades = []
    # 盈利交易
    for i in range(3):
        trades.append(TradeRecord(
            trade_id=f'win_{i}',
            order_id=f'order_{i}',
            ts_code='000001.SZ',
            side=OrderSide.SELL,
            filled_quantity=1000,
            filled_price=12.0,
            filled_time=dt,
            pnl=200 + i * 50,
            commission=5.0,
        ))
    # 亏损交易
    for i in range(2):
        trades.append(TradeRecord(
            trade_id=f'lose_{i}',
            order_id=f'order_{i+3}',
            ts_code='000002.SZ',
            side=OrderSide.SELL,
            filled_quantity=500,
            filled_price=18.0,
            filled_time=dt,
            pnl=-100 - i * 20,
            commission=5.0,
        ))
    return trades


def test_calculate_basic_stats():
    """测试基础统计"""
    trades = create_test_trades()
    stats = TradeStatistics.calculate_basic_stats(trades)
    assert stats['total_trades'] == 5
    assert stats['winning_trades'] == 3
    assert stats['losing_trades'] == 2
    assert abs(stats['win_rate'] - 3/5) < 0.001
    # 总盈亏: (200+250+300) + (-100-120) = 750 - 220 = 530
    assert abs(stats['total_pnl'] - 530) < 1
    # 平均: 530 / 5 = 106
    assert abs(stats['average_pnl'] - 106) < 1


def test_calculate_profit_ratio():
    """测试盈亏比计算"""
    trades = create_test_trades()
    ratio = TradeStatistics.calculate_profit_ratio(trades)
    # 平均赢: (200+250+300)/3 = 750/3 = 250
    # 平均输: (100+120)/2 = 110
    # 盈亏比: 250 / 110 ≈ 2.27
    assert abs(ratio['average_win'] - 250) < 1
    assert abs(ratio['average_loss'] - 110) < 1
    assert abs(ratio['profit_ratio'] - 250/110) < 0.1
    assert abs(ratio['win_rate'] - 0.6) < 0.001


def test_calculate_cumulative_pnl():
    """测试累计盈亏曲线"""
    trades = create_test_trades()
    cum = TradeStatistics.calculate_cumulative_pnl(trades)
    assert len(cum) == 5
    # 最后一个累计应该等于总和
    assert abs(cum[-1]['cumulative_pnl'] - 530) < 1
    # 每个点都有drawdown
    for item in cum:
        assert 'drawdown' in item
        assert item['drawdown'] >= 0


def test_calculate_max_drawdown():
    """测试最大回撤"""
    trades = create_test_trades()
    cum = TradeStatistics.calculate_cumulative_pnl(trades)
    max_dd = TradeStatistics.calculate_max_drawdown(cum)
    # 在这个例子中，最大回撤应该小于最终结果
    assert max_dd >= 0
    assert max_dd <= 530


def test_calculate_by_strategy():
    """测试按策略分组"""
    trades = create_test_trades()
    # 设置不同策略
    trades[0].strategy_id = 's1'
    trades[1].strategy_id = 's1'
    trades[2].strategy_id = 's2'
    trades[3].strategy_id = 's2'
    trades[4].strategy_id = 's2'
    result = TradeStatistics.calculate_by_strategy(trades)
    assert 's1' in result
    assert 's2' in result
    assert result['s1']['total_trades'] == 2
    assert result['s2']['total_trades'] == 3


def test_calculate_by_stock():
    """测试按股票分组"""
    trades = create_test_trades()
    result = TradeStatistics.calculate_by_stock(trades)
    assert '000001.SZ' in result
    assert '000002.SZ' in result
    assert result['000001.SZ']['total_trades'] == 3
    assert result['000002.SZ']['total_trades'] == 2


def test_calculate_turnover_stats():
    """测试成交额统计"""
    trades = create_test_trades()
    stats = TradeStatistics.calculate_turnover_stats(trades)
    assert stats['total_trades'] == 5
    # 成交额: 3 * 1000*12 + 2 * 500*18 = 36000 + 18000 = 54000
    assert abs(stats['total_turnover'] - 54000) < 1
    # 佣金: 5 * 5 = 25
    assert abs(stats['total_commission'] - 25) < 1


def test_to_dataframe():
    """测试转换为DataFrame"""
    trades = create_test_trades()
    df = TradeStatistics.to_dataframe(trades)
    assert len(df) == 5
    assert 'trade_id' in df.columns
    assert 'ts_code' in df.columns
    assert 'filled_price' in df.columns
    assert 'pnl' in df.columns


def test_generate_full_report():
    """测试生成完整报告"""
    trades = create_test_trades()
    report = TradeStatistics.generate_full_report(trades)
    assert 'basic' in report
    assert 'profit_ratio' in report
    assert 'max_drawdown' in report
    assert 'turnover' in report
    assert 'by_strategy' in report
    assert 'by_stock' in report
    assert 'cumulative_pnl' in report
