"""
Tushare数据源适配器
实现Tushare数据接口的对接
"""
import pandas as pd
from typing import List, Dict
import tushare as ts
import time
from datetime import datetime

from .market_collector import MarketDataCollector
from common.utils import StockCodeUtils, DateTimeUtils
from common.exceptions import DataSourceException
import logging

logger = logging.getLogger(__name__)


class TushareCollector(MarketDataCollector):
    """Tushare数据源实现"""

    def __init__(self, config: Dict):
        super().__init__(BusinessConstants.DATA_SOURCE_TUSHARE, config)
        self.api_key = config.get('api_key')
        if not self.api_key:
            raise DataSourceException("Tushare API Key未配置")

        # 初始化Tushare
        ts.set_token(self.api_key)
        self.pro = ts.pro_api()
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get('rate_limit', 100)  # 每分钟请求次数限制

    def _rate_limit_check(self):
        """请求频率限制检查"""
        now = time.time()
        # 重置每分钟计数
        if now - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = now

        if self.request_count >= self.rate_limit:
            wait_time = 60 - (now - self.last_request_time)
            if wait_time > 0:
                logger.warning(f"Tushare请求频率超限，等待{wait_time:.2f}秒")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            self._rate_limit_check()

            # 转换为Tushare格式的股票代码
            ts_codes = []
            for code in stock_codes:
                try:
                    num, exchange = StockCodeUtils.split_code(code)
                    if exchange == StockCodeUtils.EXCHANGE_SH:
                        ts_code = f"{num}.SH"
                    elif exchange == StockCodeUtils.EXCHANGE_SZ:
                        ts_code = f"{num}.SZ"
                    elif exchange == StockCodeUtils.EXCHANGE_BJ:
                        ts_code = f"{num}.BJ"
                    ts_codes.append(ts_code)
                except Exception as e:
                    logger.warning(f"无效的股票代码：{code}, 错误：{e}")
                    continue

            if not ts_codes:
                return pd.DataFrame()

            # 调用Tushare实时行情接口
            df = ts.realtime_quote(ts_codes=','.join(ts_codes))

            if df.empty:
                logger.warning("Tushare返回实时行情为空")
                return pd.DataFrame()

            # 数据格式转换
            df['stock_code'] = df['ts_code'].apply(lambda x: StockCodeUtils.normalize_code(x))
            df['time'] = pd.to_datetime(df['time'])
            df['source'] = self.source

            # 重命名字段
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'price': 'price',
                'vol': 'volume',
                'amount': 'amount',
                'bid': 'bid_price1',
                'bid_size': 'bid_volume1',
                'ask': 'ask_price1',
                'ask_size': 'ask_volume1'
            })

            # 保留需要的字段
            required_columns = [
                'stock_code', 'time', 'price', 'open', 'high', 'low',
                'volume', 'amount', 'bid_price1', 'bid_volume1',
                'ask_price1', 'ask_volume1', 'source'
            ]

            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            result_df = df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Tushare实时行情失败：{e}")
            raise DataSourceException(f"Tushare实时行情获取失败：{e}") from e

    def get_daily_quote(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    ts_code = StockCodeUtils.normalize_code(code).replace('.', '')
                    # Tushare日期格式为YYYYMMDD
                    start_date_ts = start_date.replace('-', '')
                    end_date_ts = end_date.replace('-', '')

                    df = self.pro.daily(
                        ts_code=ts_code,
                        start_date=start_date_ts,
                        end_date=end_date_ts
                    )

                    if not df.empty:
                        df['stock_code'] = code
                        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                        all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}日线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段
            result_df = result_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 添加复权因子，默认1.0
            if 'adj_factor' not in result_df.columns:
                result_df['adjust_factor'] = 1.0

            # 保留需要的字段
            required_columns = [
                'stock_code', 'trade_date', 'open', 'high', 'low', 'close',
                'volume', 'amount', 'adjust_factor'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            result_df = result_df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=['stock_code', 'trade_date', 'close', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Tushare日线行情失败：{e}")
            raise DataSourceException(f"Tushare日线行情获取失败：{e}") from e

    def get_minute_quote(self, stock_codes: List[str], start_date: str, end_date: str, period: int = 1) -> pd.DataFrame:
        """获取分钟线行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    ts_code = StockCodeUtils.normalize_code(code).replace('.', '')

                    # Tushare分钟行情接口
                    df = ts.pro_bar(
                        ts_code=ts_code,
                        freq=f"{period}min",
                        start_date=start_date.replace('-', ''),
                        end_date=end_date.replace('-', '')
                    )

                    if not df.empty:
                        df['stock_code'] = code
                        df['trade_time'] = pd.to_datetime(df['trade_time'])
                        all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}分钟线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段
            result_df = result_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 保留需要的字段
            required_columns = [
                'stock_code', 'trade_time', 'open', 'high', 'low', 'close',
                'volume', 'amount'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            result_df = result_df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=['stock_code', 'trade_time', 'close', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Tushare分钟线行情失败：{e}")
            raise DataSourceException(f"Tushare分钟线行情获取失败：{e}") from e

    def get_tick_quote(self, stock_codes: List[str], date: str) -> pd.DataFrame:
        """获取Tick行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    ts_code = StockCodeUtils.normalize_code(code).replace('.', '')

                    # Tushare Tick数据接口
                    df = ts.get_tick_data(
                        ts_code=ts_code,
                        date=date.replace('-', '')
                    )

                    if not df.empty:
                        df['stock_code'] = code
                        df['trade_time'] = pd.to_datetime(f"{date} {df['time']}")
                        all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}Tick行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段
            result_df = result_df.rename(columns={
                'price': 'price',
                'vol': 'volume',
                'amount': 'amount',
                'bid1': 'bid_price1',
                'bid1_vol': 'bid_volume1',
                'ask1': 'ask_price1',
                'ask1_vol': 'ask_volume1'
            })

            # 保留需要的字段
            required_columns = [
                'stock_code', 'trade_time', 'price', 'volume', 'amount',
                'bid_price1', 'bid_volume1', 'ask_price1', 'ask_volume1'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            result_df = result_df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=['stock_code', 'trade_time', 'price', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Tushare Tick行情失败：{e}")
            raise DataSourceException(f"Tushare Tick行情获取失败：{e}") from e
