"""
券商适配器抽象基类
定义券商接口的通用协议
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.trading_engine.base.base_order import BaseOrder, OrderStatus


class BaseBrokerAdapter(ABC):
    """券商适配器抽象基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化适配器
        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.connected: bool = False
        self.account_id: str = ""

    @abstractmethod
    def connect(self) -> bool:
        """
        连接券商
        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查是否已连接
        Returns:
            是否已连接
        """
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        获取账户信息
        Returns:
            账户信息字典，包含：
            - total_asset: 总资产
            - cash: 可用现金
            - market_value: 持仓市值
            - available_cash: 可用资金
            - frozen_cash: 冻结资金
        """
        pass

    @abstractmethod
    def get_available_cash(self) -> float:
        """
        获取可用资金
        Returns:
            可用现金
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取当前所有持仓
        Returns:
            持仓字典，key为股票代码，value为持仓信息
        """
        pass

    @abstractmethod
    def get_position(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """
        获取指定股票持仓
        Args:
            ts_code: 股票代码
        Returns:
            持仓信息，无持仓返回None
        """
        pass

    @abstractmethod
    def submit_order(self, order: BaseOrder) -> bool:
        """
        提交订单
        Args:
            order: 订单对象
        Returns:
            是否提交成功
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        Args:
            order_id: 订单ID
        Returns:
            是否取消成功
        """
        pass

    @abstractmethod
    def query_order(self, order_id: str) -> Optional[BaseOrder]:
        """
        查询订单状态
        Args:
            order_id: 订单ID
        Returns:
            订单对象，不存在返回None
        """
        pass

    @abstractmethod
    def query_orders(
        self,
        status: Optional[List[OrderStatus]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[BaseOrder]:
        """
        查询订单列表
        Args:
            status: 状态过滤，不指定返回所有
            start_time: 开始时间过滤
            end_time: 结束时间过滤
        Returns:
            订单列表
        """
        pass

    @abstractmethod
    def get_last_price(self, ts_code: str) -> Optional[float]:
        """
        获取股票最新价格
        Args:
            ts_code: 股票代码
        Returns:
            最新价格
        """
        pass

    @abstractmethod
    def get_last_prices(self, ts_codes: List[str]) -> Dict[str, Optional[float]]:
        """
        批量获取股票最新价格
        Args:
            ts_codes: 股票代码列表
        Returns:
            价格字典
        """
        pass

    @abstractmethod
    def get_commission(self, quantity: int, price: float, side: int) -> float:
        """
        计算佣金
        Args:
            quantity: 成交数量
            price: 成交价格
            side: 买卖方向
        Returns:
            佣金金额
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        Returns:
            健康状态信息
        """
        pass

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(account_id={self.account_id}, "
            f"connected={self.connected})"
        )
