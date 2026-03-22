"""
JoinQuant数据源基本面数据适配器
实现聚宽基本面数据接口的对接
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

import pandas as pd

from common.exceptions import DataSourceException
from common.utils import DateTimeUtils, StockCodeUtils

from .fundamentals_collector import FundamentalsCollector

logger = logging.getLogger(__name__)

# 模拟JoinQuant API导入，实际项目中需要安装jqdatasdk
try:
    import jqdatasdk as jq

    JOINQUANT_AVAILABLE = True
except ImportError:
    JOINQUANT_AVAILABLE = False
    logger.warning("jqdatasdk未安装，JoinQuant基本面数据源将无法使用")


class JoinQuantFundamentalsCollector(FundamentalsCollector):
    """JoinQuant基本面数据采集实现"""

    def __init__(self, config: Dict):
        super().__init__("joinquant", config)
        if not JOINQUANT_AVAILABLE:
            raise DataSourceException("jqdatasdk未安装，无法使用JoinQuant基本面数据源")

        self.username = config.get("username")
        self.password = config.get("password")
        if not self.username or not self.password:
            raise DataSourceException("JoinQuant用户名或密码未配置")

        # 初始化JoinQuant认证
        jq.auth(self.username, self.password)
        if not jq.is_auth():
            raise DataSourceException("JoinQuant认证失败")

        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get("rate_limit", 100)  # 每分钟请求次数限制

    def _rate_limit_check(self):
        """请求频率限制检查"""
        now = time.time()
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

    def get_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        """获取股票列表基本信息"""
        return self.execute_with_retry(self._get_stock_basic, list_status)

    def _get_stock_basic(self, list_status: str) -> pd.DataFrame:
        self._rate_limit_check()

        # JoinQuant获取所有股票列表
        stocks = jq.get_all_securities(["stock"])

        if stocks.empty:
            logger.warning("JoinQuant返回股票列表为空")
            return pd.DataFrame()

        # 转换格式
        stocks = stocks.reset_index()
        stocks["stock_code"] = stocks["code"].apply(lambda x: StockCodeUtils.normalize_code(x))

        # 筛选上市状态
        if list_status == "L":
            stocks = stocks[stocks["end_date"].isnull() | (stocks["end_date"] > datetime.now())]
        elif list_status == "D":
            stocks = stocks[stocks["end_date"] <= datetime.now()]

        # 重命名和选择字段
        stocks = stocks.rename(
            columns={"display_name": "name", "name": "fullname", "start_date": "list_date", "end_date": "delist_date"}
        )

        required_columns = ["stock_code", "code", "name", "fullname", "list_date", "delist_date"]
        result_df = stocks[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "name"]):
            return result_df
        return pd.DataFrame()

    def get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取每日基本面指标"""
        return self.execute_with_retry(self._get_daily_basic, stock_codes, start_date, end_date)

    def _get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        jq_codes = [StockCodeUtils.normalize_code(code) for code in stock_codes]
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        all_data = []
        for code in jq_codes:
            try:
                # JoinQuant获取每日估值数据
                df = jq.get_price(
                    code, start_date=start_dt, end_date=end_dt, fields=["capital", "turnover", "pe", "pb"]
                )
                if not df.empty:
                    df["stock_code"] = code
                    df = df.reset_index().rename(columns={"index": "trade_date"})
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}每日基本面失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 重命名字段
        result_df = result_df.rename(
            columns={
                "capital": "total_share",
                "turnover": "turnover_rate",
            }
        )

        required_columns = ["stock_code", "trade_date", "total_share", "pe", "pb", "turnover_rate"]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df[required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "trade_date"]):
            return result_df
        return pd.DataFrame()

    def get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        """获取财务报告"""
        return self.execute_with_retry(self._get_financial_report, stock_codes, report_type)

    def _get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        self._rate_limit_check()

        jq_codes = [StockCodeUtils.normalize_code(code) for code in stock_codes]
        all_data = []

        # JoinQuant提供财务报表数据接口
        # 根据report_type选择不同的表
        report_func_map = {"income": jq.get_income, "balance": jq.get_balance, "cashflow": jq.get_cash_flow}

        if report_type not in report_func_map:
            logger.error(f"不支持的财务报告类型：{report_type}")
            return pd.DataFrame()

        func = report_func_map[report_type]

        for code in jq_codes:
            try:
                df = func(code)
                if not df.empty:
                    df["stock_code"] = code
                    df = df.reset_index()
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code} {report_type}财务报告失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        if "end_date" in result_df.columns:
            result_df["end_date"] = pd.to_datetime(result_df["end_date"])

        result_df["report_type"] = report_type

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code"]):
            return result_df
        return pd.DataFrame()

    def get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取财务指标"""
        return self.execute_with_retry(self._get_financial_indicator, stock_codes, start_date, end_date)

    def _get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        jq_codes = [StockCodeUtils.normalize_code(code) for code in stock_codes]
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        all_data = []
        for code in jq_codes:
            try:
                # JoinQuant获取财务指标
                df = jq.get_fundamentals(
                    jq.query(
                        jq.indicator.roe,
                        jq.indicator.roa,
                        jq.indicator.gross_profit_margin,
                        jq.indicator.net_profit_margin,
                        jq.indicator.debt_to_assets,
                        jq.indicator.current_ratio,
                        jq.indicator.quick_ratio,
                        jq.indicator.eps,
                        jq.indicator.bps,
                    ).filter(jq.indicator.code == code),
                    date=end_dt,
                )

                if not df.empty:
                    df["stock_code"] = code
                    df["end_date"] = end_dt
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}财务指标失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 重命名字段
        result_df = result_df.rename(
            columns={
                "roe": "roe",
                "roa": "roa",
                "gross_profit_margin": "gross_margin",
                "net_profit_margin": "net_margin",
                "debt_to_assets": "debt_ratio",
                "current_ratio": "current_ratio",
                "quick_ratio": "quick_ratio",
                "eps": "eps",
                "bps": "bvps",
            }
        )

        required_columns = [
            "stock_code",
            "end_date",
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
        """获取分红送股数据"""
        return self.execute_with_retry(self._get_dividend, stock_codes)

    def _get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        self._rate_limit_check()

        jq_codes = [StockCodeUtils.normalize_code(code) for code in stock_codes]
        all_data = []

        for code in jq_codes:
            try:
                # JoinQuant获取分红拆分数据
                df = jq.get_dividend(code)
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
        if "ex_dividend_date" in result_df.columns:
            result_df["ex_date"] = pd.to_datetime(result_df["ex_dividend_date"])
        if "record_date" in result_df.columns:
            result_df["record_date"] = pd.to_datetime(result_df["record_date"])
        if "payable_date" in result_df.columns:
            result_df["pay_date"] = pd.to_datetime(result_df["payable_date"])

        required_columns = ["stock_code", "ex_date", "record_date", "pay_date", "cash", "bonus"]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        result_df = result_df.rename(columns={"cash": "dividend_per_share", "bonus": "bonus_ratio"})

        result_df = result_df[
            ["stock_code", "ex_date", "record_date", "pay_date", "dividend_per_share", "bonus_ratio"]
        ].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code"]):
            return result_df
        return pd.DataFrame()

    def get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取融资融券数据"""
        return self.execute_with_retry(self._get_margin_trading, stock_codes, start_date, end_date)

    def _get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()
        logger.warning("JoinQuant融资融券数据获取功能待完整实现")
        return pd.DataFrame()
