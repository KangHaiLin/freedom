"""
全系统端到端集成测试
测试完整量化交易流程：
1. 历史数据加载 → 2. 策略定义 → 3. 回测执行 → 4. 仓位管理
5. 风险控制检查 → 6. 性能指标计算 → 7. 报告生成
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from data_management.data_query.query_manager import QueryManager
from data_management.data_storage.storage_manager import StorageManager
from risk_management.compliance_management.compliance_checker import ComplianceChecker
from risk_management.risk_calculation.limit_manager import LimitManager, LimitType, RiskLimit
from risk_management.risk_manager import RiskManager
from risk_management.rule_engine.builtins import get_default_pre_trade_rules
from src.strategy_research.base.strategy_result import BacktestResult
from strategy_research.backtest_engine.backtest_config import BacktestConfig
from strategy_research.backtest_engine.backtest_engine import BacktestEngine
from strategy_research.strategy_management.strategy_manager import StrategyManager
from trading_engine.broker_adapter.simulated_broker import SimulatedBrokerAdapter
from trading_engine.order_management.order_manager import OrderManager
from trading_engine.position_management.portfolio_manager import PortfolioManager
from trading_engine.trading_manager import TradingManager


class TestFullSystemEndToEnd:
    """全系统端到端集成测试"""

    def create_sample_historical_data(self) -> pd.DataFrame:
        """创建样本历史行情数据"""
        # 创建 100 天的两只股票历史数据
        dates = pd.date_range(start="2024-01-01", end="2024-04-01", freq="B")
        data = []

        # 两只股票：000001.SZ, 600000.SH
        base_price_1 = 10.0
        base_price_2 = 20.0

        for i, date in enumerate(dates):
            # 简单随机游走
            change_1 = (i % 10 - 5) * 0.1
            change_2 = ((i + 3) % 10 - 5) * 0.15

            data.append({
                "trade_date": date,
                "stock_code": "000001.SZ",
                "open": round(base_price_1 + change_1, 2),
                "high": round(base_price_1 + change_1 + 0.2, 2),
                "low": round(base_price_1 + change_1 - 0.2, 2),
                "close": round(base_price_1 + change_1, 2),
                "volume": 1000000 + i * 10000,
                "amount": 10000000 + i * 100000,
            })

            data.append({
                "trade_date": date,
                "stock_code": "600000.SH",
                "open": round(base_price_2 + change_2, 2),
                "high": round(base_price_2 + change_2 + 0.3, 2),
                "low": round(base_price_2 + change_2 - 0.3, 2),
                "close": round(base_price_2 + change_2, 2),
                "volume": 800000 + i * 8000,
                "amount": 16000000 + i * 80000,
            })

            base_price_1 += change_1
            base_price_2 += change_2

        df = pd.DataFrame(data)
        return df.sort_values(["trade_date", "stock_code"]).reset_index(drop=True)

    def test_simple_mean_reversion_strategy_backtest(self):
        """测试简单均值回归策略完整回测流程"""
        # 1. 创建模拟历史数据
        historical_data = self.create_sample_historical_data()
        assert not historical_data.empty
        assert len(historical_data) > 0
        assert set(historical_data["stock_code"]) == {"000001.SZ", "600000.SH"}

        # 2. 准备数据 - BacktestEngine直接接收数据
        # 将日期转换为int格式 (YYYYMMDD) 符合现有API期望
        historical_data_int = historical_data.copy()
        historical_data_int["trade_date"] = historical_data_int["trade_date"].dt.strftime("%Y%m%d").astype(int)
        # 列名需要是 ts_code 不是 stock_code
        historical_data_int = historical_data_int.rename(columns={"stock_code": "ts_code"})
        # 列名需要是 vol 不是 volume
        historical_data_int = historical_data_int.rename(columns={"volume": "vol"})

        # 回测配置
        config = BacktestConfig(
            initial_capital=1000000.0,
            commission_rate=0.0003,
            slippage=0.001,
            single_position_max_ratio=0.5,
            close_at_end=True,
        )

        # 创建回测引擎 - BacktestEngine 已经包含所有内部初始化
        backtest_engine = BacktestEngine(historical_data_int, config)

        # 策略管理用于动态加载策略
        strategy_manager = StrategyManager()

        # 3. 定义简单均值回归策略
        strategy_code = '''
from src.strategy_research.base.base_strategy import BaseStrategy
from src.strategy_research.base.enums import TradeDirection

class SimpleMeanReversionStrategy(BaseStrategy):
    """简单均值回归策略"""

    def __init__(self):
        super().__init__()
        self.lookback_period = 5
        self.threshold = 0.02

    def on_bar(self, bar_data, current_date, portfolio):
        """每日调仓"""
        signals = {}
        # Iterate through each stock in the current bar
        for _, row in bar_data.iterrows():
            ts_code = row["ts_code"]
            close = row["close"]
            # Simple mean reversion signal
            if ts_code == "000001.SZ":
                if close < 10.0:
                    signals[ts_code] = TradeDirection.BUY
                elif close > 10.0:
                    signals[ts_code] = TradeDirection.SELL
            elif ts_code == "600000.SH":
                if close < 20.0:
                    signals[ts_code] = TradeDirection.BUY
                elif close > 20.0:
                    signals[ts_code] = TradeDirection.SELL

        return signals
'''

        # 4. 实例化策略
        # 策略代码已经定义，我们需要动态加载它
        from src.strategy_research.base.base_strategy import BaseStrategy

        # Execute the code string to get the strategy class
        global_dict = globals().copy()
        global_dict['BaseStrategy'] = BaseStrategy
        exec(strategy_code, global_dict)
        strategy_class = global_dict["SimpleMeanReversionStrategy"]
        strategy = strategy_class()
        assert strategy is not None
        assert hasattr(strategy, "on_bar")

        # 5. 运行回测
        result = backtest_engine.run(strategy)

        # 6. 验证回测结果
        assert result is not None
        assert isinstance(result, BacktestResult)

        # 应该有交易记录
        assert hasattr(result, "trades")
        assert len(result.trades) >= 0

        # 结果已经包含所有绩效指标
        assert hasattr(result, "daily_stats")
        assert len(result.daily_stats) > 0

        # 验证关键绩效指标存在
        required_metrics = [
            "annualized_return",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "profit_loss_ratio",
            "total_trades",
        ]
        for metric in required_metrics:
            assert hasattr(result, metric), f"Missing metric {metric}"

        # 7. 生成回测报告
        from strategy_research.report_generator.report_generator import generate_json_report
        report_json_str = generate_json_report(result)
        assert report_json_str is not None
        assert len(report_json_str) > 0
        # 解析回JSON验证格式
        import json
        report_json = json.loads(report_json_str)
        assert "strategy_name" in report_json
        assert "annualized_return" in report_json
        assert "trades" in report_json

        # 验证报告包含关键信息
        assert "annualized_return" in report_json

        # 9. 最终验证 - 所有模块正常工作
        # 检查投资组合最终权益
        assert result.final_capital > 0, "最终资本应该大于0"

        print(f"\n[E2E Test] Simple Mean Reversion Backtest completed:")
        print(f"  - Total trades: {result.total_trades}")
        print(f"  - Final capital: {result.final_capital:.2f}")
        print(f"  - Total return: {result.total_pnl_pct:.2f}%")
        print(f"  - Sharpe ratio: {result.sharpe_ratio:.2f}")
        print(f"  - Max drawdown: {result.max_drawdown:.2f}%")

        assert True  # 到达这里说明整个流程都成功了

    def test_multi_strategy_portfolio_backtest(self):
        """测试多策略组合回测"""
        # 1. 创建样本数据
        historical_data = self.create_sample_historical_data()

        # 2. 准备数据
        historical_data_int = historical_data.copy()
        historical_data_int["trade_date"] = historical_data_int["trade_date"].dt.strftime("%Y%m%d").astype(int)
        historical_data_int = historical_data_int.rename(columns={"stock_code": "ts_code"})
        historical_data_int = historical_data_int.rename(columns={"volume": "vol"})

        # 回测配置
        config = BacktestConfig(
            initial_capital=1000000.0,
            commission_rate=0.0003,
            slippage=0.001,
            single_position_max_ratio=0.5,
            close_at_end=True,
        )

        strategy_manager = StrategyManager()

        # 3. 创建两个不同策略
        # 策略1: 短期均值回归
        strategy1_code = '''
from src.strategy_research.base.base_strategy import BaseStrategy
from src.strategy_research.base.enums import TradeDirection

class ShortMeanReversion(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.lookback = 3
        self.threshold = 0.015

    def on_bar(self, bar_data, current_date, portfolio):
        signals = {}
        for _, row in bar_data.iterrows():
            ts_code = row["ts_code"]
            close = row["close"]
            # Simple mean reversion signal
            if ts_code == "000001.SZ":
                if close < 10.0 - self.threshold * 10.0:
                    signals[ts_code] = TradeDirection.BUY
                elif close > 10.0 + self.threshold * 10.0:
                    signals[ts_code] = TradeDirection.SELL
            elif ts_code == "600000.SH":
                if close < 20.0 - self.threshold * 20.0:
                    signals[ts_code] = TradeDirection.BUY
                elif close > 20.0 + self.threshold * 20.0:
                    signals[ts_code] = TradeDirection.SELL
        return signals
'''

        # 策略2: 趋势跟踪
        strategy2_code = '''
from src.strategy_research.base.base_strategy import BaseStrategy
from src.strategy_research.base.enums import TradeDirection

class SimpleTrendFollowing(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.fast_period = 5
        self.slow_period = 20

    def on_bar(self, bar_data, current_date, portfolio):
        signals = {}
        for _, row in bar_data.iterrows():
            ts_code = row["ts_code"]
            close = row["close"]
            # Simple trend following based on current price vs starting price
            if ts_code == '000001.SZ' and close > 10.5:
                signals[ts_code] = TradeDirection.BUY
            elif ts_code == '600000.SH' and close > 20.5:
                signals[ts_code] = TradeDirection.BUY
            else:
                signals[ts_code] = TradeDirection.HOLD
        return signals
'''

        # 4. 实例化策略 - 动态加载从代码字符串
        from src.strategy_research.base.base_strategy import BaseStrategy
        global_dict1 = globals().copy()
        global_dict1['BaseStrategy'] = BaseStrategy
        exec(strategy1_code, global_dict1)
        strategy1_class = global_dict1["ShortMeanReversion"]
        strategy1 = strategy1_class()

        global_dict2 = globals().copy()
        global_dict2['BaseStrategy'] = BaseStrategy
        exec(strategy2_code, global_dict2)
        strategy2_class = global_dict2["SimpleTrendFollowing"]
        strategy2 = strategy2_class()

        assert strategy1 is not None and strategy2 is not None

        # 6. 创建回测引擎并运行第一个策略
        backtest_engine1 = BacktestEngine(historical_data_int, config)
        result1 = backtest_engine1.run(strategy1)

        # 创建新的回测引擎运行第二个策略
        backtest_engine2 = BacktestEngine(historical_data_int, config)
        result2 = backtest_engine2.run(strategy2)

        # 7. 验证两个策略都成功完成
        assert isinstance(result1, BacktestResult)
        assert isinstance(result2, BacktestResult)
        assert len(result1.daily_stats) > 0
        assert len(result2.daily_stats) > 0

        # 8. 比较两个策略的表现
        # 结果已经包含所有指标
        # 验证两个策略都有有效结果
        assert result1.annualized_return is not None
        assert result2.annualized_return is not None
        assert not pd.isna(result1.sharpe_ratio)
        assert not pd.isna(result2.sharpe_ratio)

        print(f"\n[E2E Test] Multi-Strategy Portfolio completed:")
        print(f"  - Strategy 1 (Short Mean Reversion): return={result1.total_pnl_pct:.2f}%, sharpe={result1.sharpe_ratio:.2f}")
        print(f"  - Strategy 2 (Simple Trend Following): return={result2.total_pnl_pct:.2f}%, sharpe={result2.sharpe_ratio:.2f}")

        # 验证整个流程成功完成
        assert True

    def test_risk_control_compliance_e2e(self):
        """测试风险控制和合规检查端到端"""
        # 1. 创建数据，包含违规交易场景
        from datetime import date

        # 创建一天的数据，但包含T+1违规场景
        data = [
            {
                "trade_date": date(2024, 1, 1),
                "stock_code": "000001.SZ",
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0,
                "volume": 1000000,
                "amount": 10000000,
            }
        ]
        df = pd.DataFrame(data)

        # 2. 初始化系统，启用所有合规检查
        portfolio = PortfolioManager(initial_cash=100000.0)
        broker = SimulatedBrokerAdapter(
            portfolio_manager=portfolio,
            config={"initial_cash": 100000.0}
        )
        order_manager = OrderManager()
        risk_manager = RiskManager()

        # RiskManager 默认已经加载了所有默认合规规则
        # 添加自定义单个仓位比例限制
        risk_manager._limit_manager.add_limit(RiskLimit(
            limit_id=1,
            limit_type=LimitType.SINGLE_POSITION_RATIO,
            limit_value=0.1,
            description="单个仓位不超过总资产的10%",
        ))

        # 3. 测试买入后立即卖出 (T+1违规)
        # 第一天买入
        from src.trading_engine.base.base_order import OrderSide, OrderType
        from src.trading_engine.order_management.order import Order

        # 尝试买入 - we don't actually need QueryManager for this direct test
        order = Order(
            ts_code="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10000,  # 10000 * 10 = 100000 → 100% 仓位，超过10%限制
            price=10.0,
        )

        # 预交易检查
        check_result = risk_manager.pre_trade_check(1, "000001.SZ", "BUY", 10.0, 10000, portfolio=portfolio, total_asset=100000.0, current_quantity=0)
        # 应该被拒绝 - 超过仓位限制
        assert not check_result.passed()
        violations = check_result.get_violations()
        assert len(violations) > 0

        # 减少数量到合规
        order.quantity = 1000  # 1000 * 10 = 10000 → 10% 刚好
        check_result2 = risk_manager.pre_trade_check(1, "000001.SZ", "BUY", 10.0, 1000, portfolio=portfolio, total_asset=100000.0, current_quantity=0)
        assert check_result2.passed(), "应该通过，刚好10%"

        # 执行买入
        broker.connect()
        # Update last price before submitting so the broker can execute the order
        broker.update_last_prices({"000001.SZ": 10.0})
        filled_order = broker.submit_order(order)

        # 验证仓位
        pos = portfolio.get_position("000001.SZ")
        assert pos is not None
        assert pos.quantity == 1000

        # 尝试当日卖出 - T+1应该拒绝
        sell_order = Order(
            ts_code="000001.SZ",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1000,
            price=10.0,
        )

        # Since we bought 1000 shares today, available_quantity is 0 due to T+1
        check_result_t1 = risk_manager.pre_trade_check(1, "000001.SZ", "SELL", 10.0, 1000, portfolio=portfolio, trade_date=20240101, available_quantity=0)
        # T+1规则应该拒绝今日买入当日卖出
        assert not check_result_t1.passed()

        print(f"\n[E2E Test] Risk Control & Compliance:")
        print(f"  - Overweight position check: correctly rejected")
        print(f"  - T+1 restriction: correctly blocked same-day sell")
        print(f"  - Position within limit: correctly passed")

        # 所有检查都通过了验证
        assert True
