"""
Wind数据源适配器
实现Wind数据接口的对接
"""
import pandas as pd
from typing import List, Dict
import time
from datetime import datetime

from .market_collector import MarketDataCollector
from common.utils import StockCodeUtils, DateTimeUtils
from common.exceptions import DataSourceException
import logging

logger = logging.getLogger(__name__)

# 模拟Wind API导入，实际项目中需要安装WindPy
try:
    from WindPy import w
    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    logger.warning("WindPy未安装，Wind数据源将无法使用")


class WindCollector(MarketDataCollector):
    """Wind数据源实现"""

    def __init__(self, config: Dict):
        super().__init__("wind", config)
        if not WIND_AVAILABLE:
            raise DataSourceException("WindPy未安装，无法使用Wind数据源")

        # 初始化Wind
        self._init_wind()
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get('rate_limit', 200)  # 每分钟请求次数限制

    def _init_wind(self):
        """初始化Wind连接"""
        try:
            if not w.isconnected():
                ret = w.start()
                if ret.ErrorCode != 0:
                    raise DataSourceException(f"Wind连接失败，错误码：{ret.ErrorCode}")
                logger.info("Wind连接成功")
        except Exception as e:
            raise DataSourceException(f"Wind初始化失败：{e}") from e

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
                logger.warning(f"Wind请求频率超限，等待{wait_time:.2f}秒")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            self._rate_limit_check()

            # 转换为Wind格式的股票代码
            wind_codes = []
            for code in stock_codes:
                try:
                    num, exchange = StockCodeUtils.split_code(code)
                    if exchange == StockCodeUtils.EXCHANGE_SH:
                        wind_code = f"{num}.SH"
                    elif exchange == StockCodeUtils.EXCHANGE_SZ:
                        wind_code = f"{num}.SZ"
                    elif exchange == StockCodeUtils.EXCHANGE_BJ:
                        wind_code = f"{num}.BJ"
                    wind_codes.append(wind_code)
                except Exception as e:
                    logger.warning(f"无效的股票代码：{code}, 错误：{e}")
                    continue

            if not wind_codes:
                return pd.DataFrame()

            # 调用Wind实时行情接口
            fields = "rt_open,rt_high,rt_low,rt_last,rt_vol,rt_amt,rt_bid1,rt_bsize1,rt_ask1,rt_asize1,rt_time"
            ret = w.wsq(','.join(wind_codes), fields)

            if ret.ErrorCode != 0:
                raise DataSourceException(f"Wind实时行情查询失败，错误码：{ret.ErrorCode}")

            # 转换为DataFrame
            data = []
            for i, code in enumerate(ret.Codes):
                row = {
                    'stock_code': StockCodeUtils.normalize_code(code),
                    'time': DateTimeUtils.now().replace(
                        hour=int(ret.Data[-1][i]//10000),
                        minute=int((ret.Data[-1][i]%10000)//100),
                        second=int(ret.Data[-1][i]%100)
                    ),
                    'open': ret.Data[0][i],
                    'high': ret.Data[1][i],
                    'low': ret.Data[2][i],
                    'price': ret.Data[3][i],
                    'volume': ret.Data[4][i],
                    'amount': ret.Data[5][i],
                    'bid_price1': ret.Data[6][i],
                    'bid_volume1': ret.Data[7][i],
                    'ask_price1': ret.Data[8][i],
                    'ask_volume1': ret.Data[9][i],
                    'source': self.source
                }
                data.append(row)

            result_df = pd.DataFrame(data)

            # 数据校验
            required_columns = [
                'stock_code', 'time', 'price', 'open', 'high', 'low',
                'volume', 'amount', 'bid_price1', 'bid_volume1',
                'ask_price1', 'ask_volume1', 'source'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            if self.validate_data(result_df):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Wind实时行情失败：{e}")
            raise DataSourceException(f"Wind实时行情获取失败：{e}") from e

    def get_daily_quote(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    # 转换为Wind格式
                    num, exchange = StockCodeUtils.split_code(code)
                    wind_code = f"{num}.{exchange.upper()}"

                    # 调用Wind日线接口
                    fields = "open,high,low,close,volume,amount,adjfactor"
                    ret = w.wsd(wind_code, fields, start_date, end_date, "PriceAdj=F")

                    if ret.ErrorCode != 0:
                        logger.warning(f"获取{code}日线行情失败，错误码：{ret.ErrorCode}")
                        continue

                    # 转换为DataFrame
                    for i, trade_date in enumerate(ret.Times):
                        row = {
                            'stock_code': code,
                            'trade_date': trade_date.date(),
                            'open': ret.Data[0][i],
                            'high': ret.Data[1][i],
                            'low': ret.Data[2][i],
                            'close': ret.Data[3][i],
                            'volume': ret.Data[4][i],
                            'amount': ret.Data[5][i],
                            'adjust_factor': ret.Data[6][i] if len(ret.Data) > 6 else 1.0
                        }
                        all_data.append(row)

                except Exception as e:
                    logger.warning(f"获取{code}日线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.DataFrame(all_data)

            # 数据校验
            required_columns = [
                'stock_code', 'trade_date', 'open', 'high', 'low', 'close',
                'volume', 'amount', 'adjust_factor'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            if self.validate_data(result_df, required_columns=['stock_code', 'trade_date', 'close', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Wind日线行情失败：{e}")
            raise DataSourceException(f"Wind日线行情获取失败：{e}") from e

    def get_minute_quote(self, stock_codes: List[str], start_date: str, end_date: str, period: int = 1) -> pd.DataFrame:
        """获取分钟线行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    # 转换为Wind格式
                    num, exchange = StockCodeUtils.split_code(code)
                    wind_code = f"{num}.{exchange.upper()}"

                    # 调用Wind分钟线接口
                    fields = "open,high,low,close,volume,amount"
                    ret = w.wsi(wind_code, fields, start_date + " 09:30:00", end_date + " 15:00:00", f"BarSize={period}")

                    if ret.ErrorCode != 0:
                        logger.warning(f"获取{code}分钟线行情失败，错误码：{ret.ErrorCode}")
                        continue

                    # 转换为DataFrame
                    for i, trade_time in enumerate(ret.Times):
                        row = {
                            'stock_code': code,
                            'trade_time': trade_time,
                            'open': ret.Data[0][i],
                            'high': ret.Data[1][i],
                            'low': ret.Data[2][i],
                            'close': ret.Data[3][i],
                            'volume': ret.Data[4][i],
                            'amount': ret.Data[5][i]
                        }
                        all_data.append(row)

                except Exception as e:
                    logger.warning(f"获取{code}分钟线行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.DataFrame(all_data)

            # 数据校验
            required_columns = [
                'stock_code', 'trade_time', 'open', 'high', 'low', 'close',
                'volume', 'amount'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            if self.validate_data(result_df, required_columns=['stock_code', 'trade_time', 'close', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Wind分钟线行情失败：{e}")
            raise DataSourceException(f"Wind分钟线行情获取失败：{e}") from e

    def get_tick_quote(self, stock_codes: List[str], date: str) -> pd.DataFrame:
        """获取Tick行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    # 转换为Wind格式
                    num, exchange = StockCodeUtils.split_code(code)
                    wind_code = f"{num}.{exchange.upper()}"

                    # 调用Wind Tick接口
                    fields = "last,volume,amount,bid1,bsize1,ask1,asize1"
                    ret = w.wst(wind_code, fields, date + " 09:30:00", date + " 15:00:00")

                    if ret.ErrorCode != 0:
                        logger.warning(f"获取{code}Tick行情失败，错误码：{ret.ErrorCode}")
                        continue

                    # 转换为DataFrame
                    for i, trade_time in enumerate(ret.Times):
                        row = {
                            'stock_code': code,
                            'trade_time': trade_time,
                            'price': ret.Data[0][i],
                            'volume': ret.Data[1][i],
                            'amount': ret.Data[2][i],
                            'bid_price1': ret.Data[3][i],
                            'bid_volume1': ret.Data[4][i],
                            'ask_price1': ret.Data[5][i],
                            'ask_volume1': ret.Data[6][i]
                        }
                        all_data.append(row)

                except Exception as e:
                    logger.warning(f"获取{code}Tick行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.DataFrame(all_data)

            # 数据校验
            required_columns = [
                'stock_code', 'trade_time', 'price', 'volume', 'amount',
                'bid_price1', 'bid_volume1', 'ask_price1', 'ask_volume1'
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            if self.validate_data(result_df, required_columns=['stock_code', 'trade_time', 'price', 'volume']):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取Wind Tick行情失败：{e}")
            raise DataSourceException(f"Wind Tick行情获取失败：{e}") from e
