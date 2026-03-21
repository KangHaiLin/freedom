"""
数据采集模块
负责从各数据源采集行情、基本面等数据，完成清洗和标准化
"""
from .market_collector import MarketDataCollector
from .fundamentals_collector import FundamentalsCollector
from .tushare_collector import TushareCollector
from .tushare_fundamentals import TushareFundamentalsCollector
from .wind_collector import WindCollector
from .wind_fundamentals import WindFundamentalsCollector
from .joinquant_collector import JoinQuantCollector
from .joinquant_fundamentals import JoinQuantFundamentalsCollector
from .akshare_collector import AKShareCollector
from .akshare_fundamentals import AKShareFundamentalsCollector
from .data_source_manager import DataSourceManager, data_source_manager
from .data_cleaner import DataCleaner, data_cleaner
from .fundamentals_manager import FundamentalsManager, fundamentals_manager
from .init_data_sources import (
    init_market_data_sources,
    init_fundamentals_data_sources,
    init_all_data_sources,
    get_market_data_source_manager,
    get_fundamentals_manager,
)

__all__ = [
    'MarketDataCollector',
    'FundamentalsCollector',
    'TushareCollector',
    'TushareFundamentalsCollector',
    'WindCollector',
    'WindFundamentalsCollector',
    'JoinQuantCollector',
    'JoinQuantFundamentalsCollector',
    'AKShareCollector',
    'AKShareFundamentalsCollector',
    'DataSourceManager',
    'data_source_manager',
    'DataCleaner',
    'data_cleaner',
    'FundamentalsManager',
    'fundamentals_manager',
    'init_market_data_sources',
    'init_fundamentals_data_sources',
    'init_all_data_sources',
    'get_market_data_source_manager',
    'get_fundamentals_manager',
]
