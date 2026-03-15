"""
Unit tests for trading_manager.py
"""
import pytest
from datetime import datetime, timedelta
from src.trading_engine.trading_manager import TradingManager
from src.trading_engine.base.base_order import OrderSide, OrderType
from src.trading_engine.base.base_order import OrderStatus


def test_init_default():
    """测试默认初始化"""
    tm = TradingManager(initial_cash=100000.0)
    health = tm.health_check()
    assert health['status'] == 'ok'
    assert tm.get_total_asset() == pytest.approx(100000.0)


def test_submit_buy_order_market():
    """测试提交买入市价单"""
    tm = TradingManager(initial_cash=100000.0)
    result = tm.submit_order(
        '000001.SZ', OrderSide.BUY, 1000, 10.0, OrderType.MARKET,
    )
    assert result['success']
    order_id = result['order_id']
    order = tm.get_order(order_id)
    assert order is not None
    assert order.status == OrderStatus.FILLED
    assert len(tm.get_all_trades()) == 1

    # 检查持仓
    position = tm.get_position('000001.SZ')
    assert position is not None
    assert position['quantity'] == 1000


def test_submit_sell_order_success():
    """测试卖出成功"""
    tm = TradingManager(initial_cash=100000.0)
    # 先买入
    tm.submit_order('000001.SZ', OrderSide.BUY, 1000, 10.0, OrderType.MARKET)

    # 再卖出
    result = tm.submit_order(
        '000001.SZ', OrderSide.SELL, 500, 12.0, OrderType.MARKET,
    )
    assert result['success']
    position = tm.get_position('000001.SZ')
    assert position['quantity'] == 500
    assert len(tm.get_all_trades()) == 2


def test_submit_sell_insufficient_position():
    """测试卖出持仓不足"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0, OrderType.MARKET)
    result = tm.submit_order(
        '000001.SZ', OrderSide.SELL, 200, 12.0, OrderType.MARKET,
    )
    # 模拟券商端会拒绝
    assert not result['success']
    assert '现金不足' in result['message'] or '持仓' in result['message']


def test_risk_control_fail_max_concentration():
    """测试风控失败-超出最大持仓数量"""
    tm = TradingManager(initial_cash=100000.0)
    # 已经10只股票，再买第11只会失败
    for i in range(10):
        tm.submit_order(f'{i:06d}.SZ', OrderSide.BUY, 100, 10.0, OrderType.MARKET)
    result = tm.submit_order(
        '999999.SZ', OrderSide.BUY, 100, 10.0, OrderType.MARKET,
    )
    assert not result['success']
    assert '超出最大持仓数量' in result['message']


def test_risk_control_fail_single_position_too_large():
    """测试风控失败-单票太大"""
    tm = TradingManager(initial_cash=100000.0)
    # 买入20%，默认限制10%
    result = tm.submit_order(
        '000001.SZ', OrderSide.BUY, 2000, 10.0, OrderType.MARKET,
    )
    assert not result['success']
    assert '单票市值超出限制' in result['message']


def test_cancel_order_success():
    """测试取消成功，但模拟券商已经立即成交所以不能取消"""
    tm = TradingManager(initial_cash=100000.0)
    # 模拟券商立即成交，所以提交后就是已成交，不能取消
    result = tm.submit_order('000001.SZ', OrderSide.BUY, 1000, 10.0)
    order_id = result['order_id']
    cancel_result = tm.cancel_order(order_id)
    # 模拟券商已成交，不能取消
    assert not cancel_result['success']


def test_cancel_order_not_exist():
    """测试取消不存在订单"""
    tm = TradingManager(initial_cash=100000.0)
    result = tm.cancel_order('not-exist')
    assert not result['success']
    assert '不存在' in result['message']


def test_get_portfolio_summary():
    """测试投资组合汇总"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 500, 10.0, OrderType.MARKET)
    tm.submit_order('000002.SZ', OrderSide.BUY, 250, 20.0, OrderType.MARKET)
    summary = tm.get_portfolio_summary()
    assert 'total_asset' in summary
    assert 'total_pnl' in summary
    assert 'cash' in summary
    assert 'total_market_value' in summary
    assert summary['position_count'] == 2


def test_get_all_positions():
    """测试获取所有持仓"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0)
    tm.submit_order('000002.SZ', OrderSide.BUY, 200, 20.0)
    positions = tm.get_all_positions()
    assert len(positions) == 2
    assert '000001.SZ' in positions
    assert '000002.SZ' in positions


def test_get_trading_statistics():
    """测试交易统计"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0)
    tm.submit_order('000001.SZ', OrderSide.SELL, 100, 11.0)
    tm.submit_order('000002.SZ', OrderSide.BUY, 100, 20.0)
    tm.submit_order('000002.SZ', OrderSide.SELL, 100, 18.0)
    stats = tm.get_trading_statistics()
    assert stats['total_trades_all'] == 4
    assert 'basic' in stats
    assert 'win_rate' in stats['basic']
    assert 'total_pnl' in stats['basic']


def test_submit_vwap_order():
    """测试提交VWAP算法订单"""
    tm = TradingManager(initial_cash=100000.0)
    start = datetime.now()
    end = start + timedelta(minutes=30)
    result = tm.submit_vwap_order(
        '000001.SZ', OrderSide.BUY, 10000,
        start, end, participation_rate=0.1,
    )
    assert result['success']
    execution_id = result['execution_id']
    stats = tm.get_execution_statistics()
    assert stats['active_executions'] == 1


def test_submit_twap_order():
    """测试提交TWAP算法订单"""
    tm = TradingManager(initial_cash=100000.0)
    start = datetime.now()
    end = start + timedelta(minutes=60)
    result = tm.submit_twap_order(
        '000001.SZ', OrderSide.BUY, 6000,
        start, end, interval_seconds=300,
    )
    assert result['success']
    execution_id = result['execution_id']
    stats = tm.get_execution_statistics()
    assert stats['active_executions'] == 1


def test_cancel_execution():
    """测试取消算法执行"""
    tm = TradingManager(initial_cash=100000.0)
    start = datetime.now()
    end = start + timedelta(minutes=30)
    result = tm.submit_vwap_order(
        '000001.SZ', OrderSide.BUY, 10000, start, end,
    )
    assert result['success']
    exec_id = result['execution_id']
    cancel_result = tm.cancel_execution(exec_id)
    assert cancel_result['success']


def test_update_last_prices():
    """测试更新价格"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 1000, 10.0)
    tm.update_last_prices({'000001.SZ': 12.0})
    position = tm.get_position('000001.SZ')
    assert position['last_price'] == 12.0


def test_check_portfolio_risk_no_alert():
    """测试投资组合风险检查无警示"""
    tm = TradingManager(initial_cash=100000.0)
    result = tm.check_portfolio_risk(max_drawdown=0.2)
    assert not result['alert']


def test_get_orders_by_status():
    """测试按状态查询订单"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0)
    filled_orders = tm.get_orders_by_status(OrderStatus.FILLED)
    assert len(filled_orders) == 1


def test_get_trades_by_strategy():
    """测试按策略查询"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0, strategy_id='strat1')
    tm.submit_order('000002.SZ', OrderSide.BUY, 100, 10.0, strategy_id='strat2')
    trades1 = tm.get_trades_by_strategy('strat1')
    trades2 = tm.get_trades_by_strategy('strat2')
    assert len(trades1) == 1
    assert len(trades2) == 1


def test_health_check():
    """测试健康检查"""
    tm = TradingManager(initial_cash=100000.0)
    tm.submit_order('000001.SZ', OrderSide.BUY, 100, 10.0)
    health = tm.health_check()
    assert health['status'] == 'ok'
    assert 'stats' in health
    assert health['stats']['total_orders'] == 1
    assert health['stats']['total_trades'] == 1
    assert health['stats']['total_positions'] == 1


def test_disabled_risk_control():
    """测试禁用风控"""
    tm = TradingManager(initial_cash=100000.0, enable_risk_control=False)
    # 即使大单也能买，因为风控禁用
    # 默认风控限制10%，这里买20%
    result = tm.submit_order(
        '000001.SZ', OrderSide.BUY, 2000, 10.0, OrderType.MARKET,
    )
    # 券商模拟只检查现金，所以能通过
    assert result['success']
    assert tm.get_position('000001.SZ') is not None
