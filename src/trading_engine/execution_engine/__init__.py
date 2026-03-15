"""
执行引擎模块
算法交易，支持VWAP/TWAP订单拆分执行，减少市场冲击
- ExecutionEngine: 执行引擎主类，后台线程调度算法执行
- VWAPAlgo: VWAP成交量加权平均价格算法
- TWAPAlgo: TWAP时间加权平均价格算法
- OrderSplitter: 订单拆分器，多种拆分策略
"""
from .vwap_algo import VWAPAlgo, ParticipationVWAP
from .twap_algo import TWAPAlgo
from .order_splitter import OrderSplitter
from .execution_engine import ExecutionEngine, ExecutionAlgo, ActiveExecution

__all__ = [
    'VWAPAlgo',
    'ParticipationVWAP',
    'TWAPAlgo',
    'OrderSplitter',
    'ExecutionEngine',
    'ExecutionAlgo',
    'ActiveExecution',
]
