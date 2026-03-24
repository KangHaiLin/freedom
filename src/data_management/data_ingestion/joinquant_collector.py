"""
JoinQuant数据源适配器
实现聚宽数据接口的对接
"""

import logging
import time
from typing import Dict, List

import pandas as pd

from common.exceptions import DataSourceException
from common.utils import DateTimeUtils, StockCodeUtils

from .market_collector import MarketDataCollector

logger = logging.getLogger(__name__)

# 模拟JoinQuant API导入，实际项目中需要安装jqdatasdk
try:
    import jqdatasdk as jq

    JOINQUANT_AVAILABLE = True
except ImportError:
    JOINQUANT_AVAILABLE = False
    logger.warning("jqdatasdk未安装，JoinQuant数据源将无法使用")


class JoinQuantCollector(MarketDataCollector):
    """JoinQuant数据源实现"""

    def __init__(self, config: Dict):
        super().__init__("joinquant", config)
        if not JOINQUANT_AVAILABLE:
            raise DataSourceException("jqdatasdk未安装，无法使用JoinQuant数据源")

        self.username = config.get("username")
        self.password = config.get("password")
        if not self.username or not self.password:
            raise DataSourceException("JoinQuant用户名或密码未配置")

        # 初始化JoinQuant
        self._init_joinquant()
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get("rate_limit", 100)  # 每分钟请求次数限制

    def _init_joinquant(self):
        """初始化JoinQuant连接"""
        try:
            jq.auth(self.username, self.password)
            if not jq.is_auth():
                raise DataSourceException("JoinQuant认证失败")
            logger.info("JoinQuant连接成功")
        except Exception as e:
            raise DataSourceException(f"JoinQuant初始化失败：{e}") from e

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
                logger.warning(f"JoinQuant请求频率超限，等待{wait_time:.2f}秒")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def _convert_to_jq_code(self, code: str) -> str:
        """转换为聚宽格式的股票代码"""
        num, exchange = StockCodeUtils.split_code(code)
        if exchange == StockCodeUtils.EXCHANGE_SH:
            return f"{num}.XSHG"
        elif exchange == StockCodeUtils.EXCHANGE_SZ:
            return f"{num}.XSHE"
        elif exchange == StockCodeUtils.EXCHANGE_BJ:
            return f"{num}.BJSE"
        raise DataSourceException(f"不支持的交易所：{exchange}")

    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取实时行情"""
        try:
            self._rate_limit_check()

            # 转换为JoinQuant格式的股票代码
            jq_codes = []
            for code in stock_codes:
                try:
                    jq_code = self._convert_to_jq_code(code)
                    jq_codes.append(jq_code)
                except Exception as e:
                    logger.warning(f"无效的股票代码：{code}, 错误：{e}")
                    continue

            if not jq_codes:
                return pd.DataFrame()

            # 调用JoinQuant实时行情接口
            df = jq.get_current_price(jq_codes, include_now=True)

            if df.empty:
                logger.warning("JoinQuant返回实时行情为空")
                return pd.DataFrame()

            # 数据格式转换
            df = df.reset_index()
            df.rename(columns={"index": "jq_code"}, inplace=True)
            df["stock_code"] = df["jq_code"].apply(lambda x: StockCodeUtils.normalize_code(x))
            df["time"] = DateTimeUtils.now()
            df["source"] = self.source

            # 补充其他字段（聚宽实时接口只返回当前价，其他字段需要从快照获取）
            snapshot = jq.get_snapshot(jq_codes)
            if not snapshot.empty:
                snapshot = snapshot.reset_index()
                df = df.merge(snapshot, left_on="jq_code", right_on="code", how="left")

            # 重命名字段
            rename_map = {
                "current": "price",
                "open_x": "open",
                "high_x": "high",
                "low_x": "low",
                "volume": "volume",
                "amount": "amount",
                "a1_p": "ask_price1",
                "a1_v": "ask_volume1",
                "b1_p": "bid_price1",
                "b1_v": "bid_volume1",
            }

            for old_name, new_name in rename_map.items():
                if old_name in df.columns:
                    df[new_name] = df[old_name]

            # 保留需要的字段
            required_columns = [
                "stock_code",
                "time",
                "price",
                "open",
                "high",
                "low",
                "volume",
                "amount",
                "bid_price1",
                "bid_volume1",
                "ask_price1",
                "ask_volume1",
                "source",
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
            logger.error(f"获取JoinQuant实时行情失败：{e}")
            raise DataSourceException(f"JoinQuant实时行情获取失败：{e}") from e

    def get_daily_quote(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线行情"""
        try:
            self._rate_limit_check()

            # 转换为JoinQuant格式的股票代码
            jq_codes = []
            code_map = {}
            for code in stock_codes:
                try:
                    jq_code = self._convert_to_jq_code(code)
                    jq_codes.append(jq_code)
                    code_map[jq_code] = code
                except Exception as e:
                    logger.warning(f"无效的股票代码：{code}, 错误：{e}")
                    continue

            if not jq_codes:
                return pd.DataFrame()

            # 调用JoinQuant日线接口
            df = jq.get_price(
                jq_codes,
                start_date=start_date,
                end_date=end_date,
                frequency="daily",
                fields=["open", "high", "low", "close", "volume", "money", "factor"],
                skip_paused=False,
                fq="pre",
            )

            if df.empty:
                logger.warning("JoinQuant返回日线行情为空")
                return pd.DataFrame()

            # 数据格式转换
            df = df.reset_index()
            df["stock_code"] = df["code"].apply(lambda x: code_map.get(x, x))
            df["trade_date"] = pd.to_datetime(df["time"]).dt.date

            # 重命名字段
            df = df.rename(columns={"money": "amount", "factor": "adjust_factor"})

            # 保留需要的字段
            required_columns = [
                "stock_code",
                "trade_date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "adjust_factor",
            ]

            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            result_df = df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=["stock_code", "trade_date", "close", "volume"]):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取JoinQuant日线行情失败：{e}")
            raise DataSourceException(f"JoinQuant日线行情获取失败：{e}") from e

    def get_minute_quote(self, stock_codes: List[str], start_date: str, end_date: str, period: int = 1) -> pd.DataFrame:
        """获取分钟线行情"""
        try:
            self._rate_limit_check()

            # 转换为JoinQuant格式的股票代码
            jq_codes = []
            code_map = {}
            for code in stock_codes:
                try:
                    jq_code = self._convert_to_jq_code(code)
                    jq_codes.append(jq_code)
                    code_map[jq_code] = code
                except Exception as e:
                    logger.warning(f"无效的股票代码：{code}, 错误：{e}")
                    continue

            if not jq_codes:
                return pd.DataFrame()

            # 调用JoinQuant分钟线接口
            df = jq.get_price(
                jq_codes,
                start_date=start_date + " 09:30:00",
                end_date=end_date + " 15:00:00",
                frequency=f"{period}m",
                fields=["open", "high", "low", "close", "volume", "money"],
                skip_paused=False,
            )

            if df.empty:
                logger.warning("JoinQuant返回分钟线行情为空")
                return pd.DataFrame()

            # 数据格式转换
            df = df.reset_index()
            df["stock_code"] = df["code"].apply(lambda x: code_map.get(x, x))
            df["trade_time"] = pd.to_datetime(df["time"])

            # 重命名字段
            df = df.rename(columns={"money": "amount"})

            # 保留需要的字段
            required_columns = ["stock_code", "trade_time", "open", "high", "low", "close", "volume", "amount"]

            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            result_df = df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=["stock_code", "trade_time", "close", "volume"]):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取JoinQuant分钟线行情失败：{e}")
            raise DataSourceException(f"JoinQuant分钟线行情获取失败：{e}") from e

    def get_tick_quote(self, stock_codes: List[str], date: str) -> pd.DataFrame:
        """获取Tick行情"""
        try:
            self._rate_limit_check()

            all_data = []
            for code in stock_codes:
                try:
                    jq_code = self._convert_to_jq_code(code)

                    # 调用JoinQuant Tick接口
                    df = jq.get_ticks(
                        jq_code,
                        start_dt=date + " 09:30:00",
                        end_dt=date + " 15:00:00",
                        fields=["time", "current", "volume", "amount", "b1_p", "b1_v", "a1_p", "a1_v"],
                        skip=False,
                    )

                    if not df.empty:
                        df["stock_code"] = code
                        df["trade_time"] = pd.to_datetime(df["time"])
                        all_data.append(df)

                except Exception as e:
                    logger.warning(f"获取{code}Tick行情失败：{e}")
                    continue

            if not all_data:
                return pd.DataFrame()

            result_df = pd.concat(all_data, ignore_index=True)

            # 重命名字段
            result_df = result_df.rename(
                columns={
                    "current": "price",
                    "b1_p": "bid_price1",
                    "b1_v": "bid_volume1",
                    "a1_p": "ask_price1",
                    "a1_v": "ask_volume1",
                }
            )

            # 保留需要的字段
            required_columns = [
                "stock_code",
                "trade_time",
                "price",
                "volume",
                "amount",
                "bid_price1",
                "bid_volume1",
                "ask_price1",
                "ask_volume1",
            ]

            for col in required_columns:
                if col not in result_df.columns:
                    result_df[col] = None

            result_df = result_df[required_columns].copy()

            # 数据校验
            if self.validate_data(result_df, required_columns=["stock_code", "trade_time", "price", "volume"]):
                return result_df
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取JoinQuant Tick行情失败：{e}")
            raise DataSourceException(f"JoinQuant Tick行情获取失败：{e}") from e
