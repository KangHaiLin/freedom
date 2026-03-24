"""
基础策略抽象基类
所有具体策略都必须继承此类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pandas import DataFrame

from .enums import TradeDirection


class BaseStrategy(ABC):
    """策略抽象基类"""

    def __init__(self, strategy_name: str = "", params: Optional[Dict[str, Any]] = None):
        """
        初始化策略

        Args:
            strategy_name: 策略名称
            params: 策略参数字典
        """
        self.strategy_name = strategy_name or self.__class__.__name__
        self.params = params or {}
        self.initialized = False

    def initialize(self) -> None:
        """
        策略初始化，在回测/模拟开始前调用
        可以在这里初始化指标、状态变量等
        """
        self.initialized = True

    @abstractmethod
    def on_bar(
        self,
        bar_data: DataFrame,
        current_date,
        portfolio,
    ) -> Dict[str, TradeDirection]:
        """
        处理每一根K线，产生交易信号

        Args:
            bar_data: 当前K线数据，包含所有股票的OHLCV
            current_date: 当前日期
            portfolio: 当前投资组合对象

        Returns:
            交易信号字典 {ts_code: 交易方向}
        """
        pass

    def on_order(
        self,
        order,
        portfolio,
    ) -> None:
        """
        订单创建后回调

        Args:
            order: 订单对象
            portfolio: 当前投资组合
        """
        pass

    def on_trade(
        self,
        trade,
        portfolio,
    ) -> None:
        """
        成交后回调

        Args:
            trade: 成交记录
            portfolio: 当前投资组合
        """
        pass

    def on_backtest_end(
        self,
        portfolio,
        trades: List[Any],
    ) -> Dict[str, Any]:
        """
        回测结束后回调，可以做额外分析

        Args:
            portfolio: 最终投资组合
            trades: 所有成交记录

        Returns:
            额外分析结果字典
        """
        return {}

    def get_parameters(self) -> Dict[str, Any]:
        """获取当前参数"""
        return self.params.copy()

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """设置参数"""
        self.params.update(params)

    @property
    def name(self) -> str:
        """获取策略名称"""
        return self.strategy_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.strategy_name}', params={self.params})"
