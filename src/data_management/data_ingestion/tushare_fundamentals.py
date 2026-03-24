"""
Tushare数据源基本面数据适配器
实现Tushare基本面数据接口的对接
"""

import logging
import time
from typing import Dict, List

import pandas as pd
import tushare as ts

from common.constants import BusinessConstants
from common.exceptions import DataSourceException
from common.utils import StockCodeUtils

from .fundamentals_collector import FundamentalsCollector

logger = logging.getLogger(__name__)


class TushareFundamentalsCollector(FundamentalsCollector):
    """Tushare基本面数据采集实现"""

    def __init__(self, config: Dict):
        super().__init__(BusinessConstants.DATA_SOURCE_TUSHARE, config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise DataSourceException("Tushare API Key未配置")

        # 初始化Tushare
        ts.set_token(self.api_key)
        self.pro = ts.pro_api()
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get("rate_limit", 80)  # 每分钟请求次数限制

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

    def get_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        """
        获取股票列表基本信息
        Args:
            list_status: 上市状态 L-上市，D-退市，P-暂停上市
        Returns:
            包含股票基本信息的DataFrame
        """
        return self.execute_with_retry(self._get_stock_basic, list_status)

    def _get_stock_basic(self, list_status: str) -> pd.DataFrame:
        self._rate_limit_check()

        # 调用Tushare接口
        df = self.pro.stock_basic(list_status=list_status)

        if df.empty:
            logger.warning("Tushare返回股票列表为空")
            return pd.DataFrame()

        # 格式转换
        df["stock_code"] = df["ts_code"].apply(lambda x: StockCodeUtils.normalize_code(x))

        # 重命名字段，标准化输出
        df = df.rename(
            columns={
                "name": "name",
                "fullname": "fullname",
                "enname": "enname",
                "industry": "industry",
                "industry": "industry",
                "market": "market",
                "list_date": "list_date",
                "delist_date": "delist_date",
                "is_hs": "is_hs",
                "curr_type": "curr_type",
            }
        )

        # 转换日期格式
        if "list_date" in df.columns:
            df["list_date"] = pd.to_datetime(df["list_date"], format="%Y%m%d")
        if "delist_date" in df.columns:
            df["delist_date"] = pd.to_datetime(df["delist_date"], format="%Y%m%d", errors="coerce")

        # 保留需要的字段
        required_columns = [
            "stock_code",
            "ts_code",
            "name",
            "fullname",
            "enname",
            "industry",
            "market",
            "list_date",
            "delist_date",
            "is_hs",
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = None

        result_df = df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "name"]):
            return result_df
        return pd.DataFrame()

    def get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取每日基本面指标（市值、换手率、PE、PB等）
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含每日基本面的DataFrame
        """
        return self.execute_with_retry(self._get_daily_basic, stock_codes, start_date, end_date)

    def _get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        all_data = []
        start_date_ts = start_date.replace("-", "")
        end_date_ts = end_date.replace("-", "")

        for code in stock_codes:
            try:
                ts_code = StockCodeUtils.normalize_code(code).replace(".", "")

                df = self.pro.daily_basic(ts_code=ts_code, start_date=start_date_ts, end_date=end_date_ts)

                if not df.empty:
                    df["stock_code"] = code
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}每日基本面失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式
        result_df["trade_date"] = pd.to_datetime(result_df["trade_date"], format="%Y%m%d")

        # 重命名字段
        result_df = result_df.rename(
            columns={
                "total_share": "total_share",
                "float_share": "float_share",
                "total_mv": "total_mv",
                "circ_mv": "circ_mv",
                "pe": "pe",
                "pb": "pb",
                "turnover_rate": "turnover_rate",
            }
        )

        # 保留需要的字段
        required_columns = [
            "stock_code",
            "trade_date",
            "total_share",
            "float_share",
            "total_mv",
            "circ_mv",
            "pe",
            "pb",
            "turnover_rate",
        ]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "trade_date"]):
            return result_df
        return pd.DataFrame()

    def get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        """
        获取财务报告（资产负债表、利润表、现金流量表）
        Args:
            stock_codes: 股票代码列表
            report_type: 报告类型 'income'利润表, 'balance'资产负债表, 'cashflow'现金流量表
        Returns:
            包含财务报告数据的DataFrame
        """
        return self.execute_with_retry(self._get_financial_report, stock_codes, report_type)

    def _get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        self._rate_limit_check()

        all_data = []
        api_map = {"income": self.pro.income, "balance": self.pro.balance, "cashflow": self.pro.cashflow}

        if report_type not in api_map:
            logger.error(f"不支持的财务报告类型：{report_type}")
            return pd.DataFrame()

        api_func = api_map[report_type]

        for code in stock_codes:
            try:
                ts_code = StockCodeUtils.normalize_code(code).replace(".", "")

                df = api_func(ts_code=ts_code)
                if not df.empty:
                    df["stock_code"] = code
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code} {report_type}财务报告失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式
        if "end_date" in result_df.columns:
            result_df["end_date"] = pd.to_datetime(result_df["end_date"], format="%Y%m%d")
        if "ann_date" in result_df.columns:
            result_df["ann_date"] = pd.to_datetime(result_df["ann_date"], format="%Y%m%d")

        # 添加report_type
        result_df["report_type"] = report_type

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "end_date"]):
            return result_df
        return pd.DataFrame()

    def get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取财务指标（ROE、ROA、毛利率、净利率等）
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含财务指标的DataFrame
        """
        return self.execute_with_retry(self._get_financial_indicator, stock_codes, start_date, end_date)

    def _get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        all_data = []
        start_date_ts = start_date.replace("-", "")
        end_date_ts = end_date.replace("-", "")

        for code in stock_codes:
            try:
                ts_code = StockCodeUtils.normalize_code(code).replace(".", "")

                df = self.pro.fina_indicator(ts_code=ts_code, start_date=start_date_ts, end_date=end_date_ts)

                if not df.empty:
                    df["stock_code"] = code
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}财务指标失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式
        result_df["end_date"] = pd.to_datetime(result_df["end_date"], format="%Y%m%d")
        if "ann_date" in result_df.columns:
            result_df["ann_date"] = pd.to_datetime(result_df["ann_date"], format="%Y%m%d")

        # 重命名关键指标字段（保持接口标准化）
        rename_map = {
            "roe": "roe",
            "roa": "roa",
            "gross_margin": "gross_margin",
            "net_profit_margin": "net_margin",
            "debt_to_assets": "debt_ratio",
            "current_ratio": "current_ratio",
            "quick_ratio": "quick_ratio",
            "eps": "eps",
            "bvps": "bvps",
        }
        result_df = result_df.rename(columns=rename_map)

        # 保留标准字段
        required_columns = [
            "stock_code",
            "end_date",
            "ann_date",
            "roe",
            "roa",
            "gross_margin",
            "net_margin",
            "debt_ratio",
            "current_ratio",
            "quick_ratio",
            "eps",
            "bvps",
        ]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "end_date"]):
            return result_df
        return pd.DataFrame()

    def get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取分红送股数据
        Args:
            stock_codes: 股票代码列表
        Returns:
            包含分红数据的DataFrame
        """
        return self.execute_with_retry(self._get_dividend, stock_codes)

    def _get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        self._rate_limit_check()

        all_data = []

        for code in stock_codes:
            try:
                ts_code = StockCodeUtils.normalize_code(code).replace(".", "")

                df = self.pro.dividend(ts_code=ts_code)

                if not df.empty:
                    df["stock_code"] = code
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}分红数据失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式
        date_columns = ["div_proc", "ex_date", "record_date", "pay_date"]
        for col in date_columns:
            if col in result_df.columns:
                result_df[col] = pd.to_datetime(result_df[col], format="%Y%m%d", errors="coerce")

        # 重命名字段
        result_df = result_df.rename(
            columns={
                "ex_date": "ex_date",
                "cash_div": "dividend_per_share",
                "stock_div": "bonus_ratio",
                "record_date": "record_date",
                "pay_date": "pay_date",
            }
        )

        # 保留需要的字段
        required_columns = ["stock_code", "ex_date", "record_date", "pay_date", "dividend_per_share", "bonus_ratio"]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code"]):
            return result_df
        return pd.DataFrame()

    def get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取融资融券数据
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含融资融券数据的DataFrame
        """
        return self.execute_with_retry(self._get_margin_trading, stock_codes, start_date, end_date)

    def _get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        all_data = []
        start_date_ts = start_date.replace("-", "")
        end_date_ts = end_date.replace("-", "")

        # Tushare的融资融券数据接口需要按日期批量获取
        # 先获取整体数据再按股票代码筛选
        try:
            df = self.pro.margin(start_date=start_date_ts, end_date=end_date_ts)

            if df.empty:
                logger.warning("Tushare返回融资融券数据为空")
                return pd.DataFrame()

            # 转换股票代码
            df["stock_code"] = df["ts_code"].apply(lambda x: StockCodeUtils.normalize_code(x))

            # 如果指定了股票代码，筛选
            if stock_codes:
                df = df[df["stock_code"].isin(stock_codes)]

            all_data = [df]

        except Exception as e:
            logger.error(f"获取融资融券数据失败：{e}")
            return pd.DataFrame()

        if not all_data or all_data[0].empty:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式
        result_df["trade_date"] = pd.to_datetime(result_df["trade_date"], format="%Y%m%d")

        # 重命名字段
        result_df = result_df.rename(
            columns={
                "rzye": "margin_balance",
                "rqye": "short_balance",
                "mzmch": "margin_buy",
                "sse": "margin_loan",
                "rzmcl": "margin_repay",
            }
        )

        # 保留需要的字段
        required_columns = ["stock_code", "trade_date", "margin_balance", "margin_buy", "margin_loan", "short_balance"]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "trade_date"]):
            return result_df
        return pd.DataFrame()
