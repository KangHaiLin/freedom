"""
数据源初始化模块
根据配置自动初始化并注册所有可用数据源，设置正确的优先级
优先级规则：数字越小优先级越高
默认优先级：AKShare(1) > Tushare(5) > Wind(10) > JoinQuant(15)
"""
import logging
from typing import Dict, Optional

from common.config import config
from .data_source_manager import data_source_manager
from .fundamentals_manager import fundamentals_manager
from .akshare_collector import AKShareCollector
from .akshare_fundamentals import AKShareFundamentalsCollector
from .tushare_collector import TushareCollector
from .tushare_fundamentals import TushareFundamentalsCollector
from .wind_collector import WindCollector
from .wind_fundamentals import WindFundamentalsCollector
from .joinquant_collector import JoinQuantCollector
from .joinquant_fundamentals import JoinQuantFundamentalsCollector

logger = logging.getLogger(__name__)


def init_market_data_sources() -> None:
    """初始化并注册所有行情数据源"""
    ds_config = config.data_sources

    # 初始化AKShare（不需要API Key，总是可用）
    akshare_config = {
        'priority': ds_config['akshare_priority'],
        'weight': ds_config['akshare_weight'],
        'rate_limit': 200,  # 每分钟请求次数限制
    }
    try:
        akshare = AKShareCollector(akshare_config)
        data_source_manager.add_source(akshare)
        logger.info(f"行情数据源AKShare注册成功，优先级={ds_config['akshare_priority']}, 权重={ds_config['akshare_weight']}")
    except Exception as e:
        logger.error(f"行情数据源AKShare初始化失败: {e}")

    # 初始化Tushare（如果配置了API Key）
    if ds_config['tushare_api_key']:
        tushare_config = {
            'api_key': ds_config['tushare_api_key'],
            'priority': ds_config['tushare_priority'],
            'weight': ds_config['tushare_weight'],
            'rate_limit': 100,
        }
        try:
            tushare = TushareCollector(tushare_config)
            data_source_manager.add_source(tushare)
            logger.info(f"行情数据源Tushare注册成功，优先级={ds_config['tushare_priority']}, 权重={ds_config['tushare_weight']}")
        except Exception as e:
            logger.error(f"行情数据源Tushare初始化失败: {e}")

    # 初始化Wind（如果配置了API Key）
    if ds_config['wind_api_key']:
        wind_config = {
            'api_key': ds_config['wind_api_key'],
            'priority': ds_config['wind_priority'],
            'weight': ds_config['wind_weight'],
            'rate_limit': 80,
        }
        try:
            wind = WindCollector(wind_config)
            data_source_manager.add_source(wind)
            logger.info(f"行情数据源Wind注册成功，优先级={ds_config['wind_priority']}, 权重={ds_config['wind_weight']}")
        except Exception as e:
            logger.error(f"行情数据源Wind初始化失败: {e}")

    # 初始化JoinQuant（如果配置了API Key）
    if ds_config['joinquant_api_key']:
        joinquant_config = {
            'api_key': ds_config['joinquant_api_key'],
            'priority': ds_config['joinquant_priority'],
            'weight': ds_config['joinquant_weight'],
            'rate_limit': 50,
        }
        try:
            joinquant = JoinQuantCollector(joinquant_config)
            data_source_manager.add_source(joinquant)
            logger.info(f"行情数据源JoinQuant注册成功，优先级={ds_config['joinquant_priority']}, 权重={ds_config['joinquant_weight']}")
        except Exception as e:
            logger.error(f"行情数据源JoinQuant初始化失败: {e}")

    logger.info(f"行情数据源初始化完成，共注册{len(data_source_manager.sources)}个数据源")


def init_fundamentals_data_sources() -> None:
    """初始化并注册所有基本面数据源"""
    ds_config = config.data_sources

    # 初始化AKShare基本面数据（不需要API Key）
    akshare_config = {
        'priority': ds_config['akshare_priority'],
        'weight': ds_config['akshare_weight'],
        'rate_limit': 100,
    }
    try:
        akshare = AKShareFundamentalsCollector(akshare_config)
        fundamentals_manager.add_source(akshare)
        logger.info(f"基本面数据源AKShare注册成功，优先级={ds_config['akshare_priority']}, 权重={ds_config['akshare_weight']}")
    except Exception as e:
        logger.error(f"基本面数据源AKShare初始化失败: {e}")

    # 初始化Tushare基本面数据（如果配置了API Key）
    if ds_config['tushare_api_key']:
        tushare_config = {
            'api_key': ds_config['tushare_api_key'],
            'priority': ds_config['tushare_priority'],
            'weight': ds_config['tushare_weight'],
            'rate_limit': 80,
        }
        try:
            tushare = TushareFundamentalsCollector(tushare_config)
            fundamentals_manager.add_source(tushare)
            logger.info(f"基本面数据源Tushare注册成功，优先级={ds_config['tushare_priority']}, 权重={ds_config['tushare_weight']}")
        except Exception as e:
            logger.error(f"基本面数据源Tushare初始化失败: {e}")

    # 初始化Wind基本面数据（如果配置了API Key）
    if ds_config['wind_api_key']:
        wind_config = {
            'api_key': ds_config['wind_api_key'],
            'priority': ds_config['wind_priority'],
            'weight': ds_config['wind_weight'],
            'rate_limit': 50,
        }
        try:
            wind = WindFundamentalsCollector(wind_config)
            fundamentals_manager.add_source(wind)
            logger.info(f"基本面数据源Wind注册成功，优先级={ds_config['wind_priority']}, 权重={ds_config['wind_weight']}")
        except Exception as e:
            logger.error(f"基本面数据源Wind初始化失败: {e}")

    # 初始化JoinQuant基本面数据（如果配置了API Key）
    if ds_config['joinquant_api_key']:
        joinquant_config = {
            'api_key': ds_config['joinquant_api_key'],
            'priority': ds_config['joinquant_priority'],
            'weight': ds_config['joinquant_weight'],
            'rate_limit': 30,
        }
        try:
            joinquant = JoinQuantFundamentalsCollector(joinquant_config)
            fundamentals_manager.add_source(joinquant)
            logger.info(f"基本面数据源JoinQuant注册成功，优先级={ds_config['joinquant_priority']}, 权重={ds_config['joinquant_weight']}")
        except Exception as e:
            logger.error(f"基本面数据源JoinQuant初始化失败: {e}")

    logger.info(f"基本面数据源初始化完成，共注册{len(fundamentals_manager.sources)}个数据源")


def init_all_data_sources() -> None:
    """初始化所有数据源"""
    init_market_data_sources()
    init_fundamentals_data_sources()
    total_market = len(data_source_manager.sources)
    total_fundamental = len(fundamentals_manager.sources)
    logger.info(f"所有数据源初始化完成：行情 {total_market} 个，基本面 {total_fundamental} 个")


def get_market_data_source_manager():
    """获取行情数据源管理器"""
    return data_source_manager


def get_fundamentals_manager():
    """获取基本面数据源管理器"""
    return fundamentals_manager


# 导出
__all__ = [
    'init_market_data_sources',
    'init_fundamentals_data_sources',
    'init_all_data_sources',
    'get_market_data_source_manager',
    'get_fundamentals_manager',
]
