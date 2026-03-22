"""
券商适配器模块
- CommissionConfig: 佣金配置
- CommissionCalculator: A股标准佣金计算器
- BrokerInterface: 券商接口常量定义
- SimulatedBrokerAdapter: 模拟券商适配器（用于回测/模拟）
- BrokerAdapterManager: 券商适配器管理器，管理多个适配器
"""

from .broker_adapter_manager import BrokerAdapterManager
from .interface import BrokerInterface, CommissionCalculator, CommissionConfig
from .simulated_broker import SimulatedBrokerAdapter

__all__ = [
    "CommissionConfig",
    "CommissionCalculator",
    "BrokerInterface",
    "SimulatedBrokerAdapter",
    "BrokerAdapterManager",
]
