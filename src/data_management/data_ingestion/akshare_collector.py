"""
AKShare数据源适配器
实现AKShare数据接口的对接
AKShare是开源免费的财经数据接口库，不需要API Key
"""
import pandas as pd
from typing import List, Dict
import akshare as ak
import time

from .market_collector import MarketDataCollector
from common.constants import BusinessConstants
from common.utils import StockCodeUtils, DateTimeUtils
from common.exceptions import DataSourceException
import logging

logger = logging.getLogger(__name__)


class AKShareCollector(MarketDataCollector):
    """AKShare数据源实现"""

    def __init__(self, config: Dict):
        super().__init__(BusinessConstants.DATA_SOURCE_AKSHARE, config)
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get('rate_limit', 200)  # 每分钟请求次数限制
        self._stock_code_cache: Dict[str, str] = {}  # 代码转换缓存

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
                logger.warning(f"AKShare请求频率超限，等待{wait_time:.2f}秒")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def _convert_stock_code(self, code: str) -> str:
        """转换为AKShare格式的股票代码

        AKShare使用格式：sh600000 或 sz000001
        """
        if code in self._stock_code_cache:
            return self._stock_code_cache[code]

        try:
            num, exchange = StockCodeUtils.split_code(code)
            if exchange == StockCodeUtils.EXCHANGE_SH:
                result = f"sh{num}"
            elif exchange == StockCodeUtils.EXCHANGE_SZ:
                result = f"sz{num}"
            elif exchange == StockCodeUtils.EXCHANGE_BJ:
                result = f"bj{num}"
            else:
                result = code
            self._stock_code_cache[code] = result
            return result
        except Exception as e:
            logger.warning(f"无效的股票代码：{code}, 错误：{e}")
            return code

    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            self._rate_limit_check()

            # 获取东方财富网实时行情
            df = ak.stock_zh_a_spot()

            if df.empty:
                logger.warning("AKShare返回实时行情为空")
                return pd.DataFrame()

            # 筛选指定股票
            target_codes = [self._convert_stock_code(code) for code in stock_codes]
            df = df[df['代码'].isin(target_codes)]

            if df.empty:
                logger.warning("指定的股票代码未找到行情")
                return pd.DataFrame()

            # 转换代码格式回系统标准格式
            def _normalize_code(ak_code: str) -> str:
                prefix = ak_code[:2]
                code = ak_code[2:]
                if prefix == 'sh':
                    return f"{code}.{StockCodeUtils.EXCHANGE_SH}"
                elif prefix == 'sz':
                    return f"{code}.{StockCodeUtils.EXCHANGE_SZ}"
                elif prefix == 'bj':
                    return f"{code}.{StockCodeUtils.EXCHANGE_BJ}"
                return ak_code

            df['stock_code'] = df['代码'].apply(_normalize_code)
            now_time = DateTimeUtils.now()
            df['time'] = now_time

            # 重命名字段，标准化输出
            df = df.rename(columns={
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '最新': 'price',
                '成交量': 'volume',
                '成交额': 'amount',
            })

            # AKShare不提供买卖盘口数据，设为None
            df['bid_price1'] = None
            df['bid_volume1'] = None
            df['ask_price1'] = None
            df['ask_volume1'] = None

            # 添加数据源标记
            df['source'] = self.source

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
            logger.error(f"获取AKShare实时行情失败：{e}")
            raise DataSourceException(f"AKShare实时行情获取失败：{e}") from e

    def get_daily_quote(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线行情"""
        try:
            all_data = []

            for code in stock_codes:
                try:
                    self._rate_limit_check()

                    ak_code = self._convert_stock_code(code)
                    # AKShare获取历史行情
                    df = ak.stock_zh_a_daily(symbol=ak_code, start_date=start_date, end_date=end_date, adjust="qfq")

                    if not df.empty:
                        df['stock_code'] = code
                        df.index.name = 'trade_date'
                        df = df.reset_index()
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}日线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段，标准化输出
            result_df = result_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount'
            })

            # 添加复权因子，AKShare默认前复权，这里无法获取复权因子设为1.0
            if 'adjust_factor' not in result_df.columns:
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
            logger.error(f"获取AKShare日线行情失败：{e}")
            raise DataSourceException(f"AKShare日线行情获取失败：{e}") from e

    def get_minute_quote(self, stock_codes: List[str], start_date: str, end_date: str, period: int = 1) -> pd.DataFrame:
        """获取分钟线行情"""
        try:
            all_data = []

            for code in stock_codes:
                try:
                    self._rate_limit_check()

                    ak_code = self._convert_stock_code(code)

                    # AKShare获取分钟线，period参数转换
                    period_map = {
                        1: '1min',
                        5: '5min',
                        15: '15min',
                        30: '30min',
                        60: '60min'
                    }
                    period_str = period_map.get(period, '1min')

                    # 获取分钟线数据
                    df = ak.stock_zh_a_minute(symbol=ak_code, period=period_str)

                    if not df.empty:
                        # 按日期范围筛选
                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

                        if not df.empty:
                            df['stock_code'] = code
                            df = df.rename(columns={'date': 'trade_time'})
                            all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}分钟线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段，标准化输出
            result_df = result_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
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
            logger.error(f"获取AKShare分钟线行情失败：{e}")
            raise DataSourceException(f"AKShare分钟线行情获取失败：{e}") from e

    def get_tick_quote(self, stock_codes: List[str], date: str) -> pd.DataFrame:
        """获取Tick行情"""
        try:
            all_data = []

            for code in stock_codes:
                try:
                    self._rate_limit_check()

                    ak_code = self._convert_stock_code(code)

                    # AKShare获取分时Tick数据
                    df = ak.stock_zh_a_tick_tx_js(symbol=ak_code)

                    if not df.empty:
                        # 按日期筛选
                        df['trade_time'] = pd.to_datetime(df['成交时间'])
                        target_date = pd.to_datetime(date)
                        df = df[df['trade_time'].dt.date == target_date.date()]

                        if not df.empty:
                            df['stock_code'] = code
                            all_data.append(df)
                except Exception as e:
                    logger.warning(f"获取{code}Tick行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段，标准化输出
            result_df = result_df.rename(columns={
                '成交价': 'price',
                '成交量': 'volume',
                '成交额': 'amount',
                'price': 'price',
                'volume': 'volume',
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
            logger.error(f"获取AKShare Tick行情失败：{e}")
            raise DataSourceException(f"AKShare Tick行情获取失败：{e}") from e
