"""
AKShare数据源基本面数据适配器
实现AKShare基本面数据接口的对接
"""

import logging
import time
from typing import Dict, List

import akshare as ak
import pandas as pd

from common.constants import BusinessConstants
from common.utils import StockCodeUtils

from .fundamentals_collector import FundamentalsCollector

logger = logging.getLogger(__name__)


class AKShareFundamentalsCollector(FundamentalsCollector):
    """AKShare基本面数据采集实现"""

    def __init__(self, config: Dict):
        super().__init__(BusinessConstants.DATA_SOURCE_AKSHARE, config)
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get("rate_limit", 120)  # 每分钟请求次数限制
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

    def _convert_stock_code_ak(self, code: str) -> str:
        """转换为AKShare格式的股票代码

        AKShare部分接口使用格式：sh600000 或 sz000001
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

        # 调用AKShare接口获取A股股票列表
        df = ak.stock_info_a_code_name()

        if df.empty:
            logger.warning("AKShare返回股票列表为空")
            return pd.DataFrame()

        # 获取交易所信息
        def _get_exchange(code: str) -> str:
            if code.startswith("60") or code.startswith("688"):
                return StockCodeUtils.EXCHANGE_SH
            elif code.startswith("00") or code.startswith("30"):
                return StockCodeUtils.EXCHANGE_SZ
            elif code.startswith("8") or code.startswith("4"):
                return StockCodeUtils.EXCHANGE_BJ
            else:
                return ""

        # 标准化代码
        def _format_code(code: str) -> str:
            exchange = _get_exchange(code)
            return f"{code}.{exchange}" if exchange else code

        df["stock_code"] = df["code"].apply(_format_code)
        df["ts_code"] = df["stock_code"]

        # AKShare不提供这些详细信息，设为None
        df["fullname"] = None
        df["enname"] = None
        df["industry"] = None
        df["market"] = None
        df["list_date"] = None
        df["delist_date"] = None
        df["is_hs"] = None

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

        # 根据上市状态筛选（AKShare只返回当前上市的）
        # AKShare不区分状态，这里默认返回上市状态
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
        all_data = []

        for code in stock_codes:
            try:
                self._rate_limit_check()

                # AKShare获取A股每日指标
                ak_code = self._convert_stock_code_ak(code)
                df = ak.stock_zh_a_daily(symbol=ak_code, start_date=start_date, end_date=end_date)

                if not df.empty:
                    # 获取市盈率、市净率等信息需要从其他接口获取
                    # AKShare的stock_zh_a_daily已经包含这些数据
                    df["stock_code"] = code
                    df.index.name = "trade_date"
                    df = df.reset_index()
                    df["trade_date"] = pd.to_datetime(df["trade_date"])
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code}每日基本面失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 重命名字段，标准化输出
        rename_map = {
            "outstanding_share": "float_share",
            "total_share": "total_share",
            "outstanding_share": "float_share",
            "total_mv": "total_mv",
            "circ_mv": "circ_mv",
            "pe": "pe",
            "pb": "pb",
            "turnover": "turnover_rate",
        }

        for col in rename_map:
            if col in result_df.columns:
                result_df = result_df.rename(columns={col: rename_map[col]})

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
        # AKShare接口名称映射（新浪财经接口）
        api_func_map = {
            "income": ak.stock_profit_sheet_by_report_em,
            "balance": ak.stock_balance_sheet_by_report_em,
            "cashflow": ak.stock_cash_flow_sheet_by_report_em,
        }

        if report_type not in api_func_map:
            logger.error(f"不支持的财务报告类型：{report_type}")
            return pd.DataFrame()

        api_func = api_func_map[report_type]

        for code in stock_codes:
            try:
                self._rate_limit_check()

                # AKShare使用纯数字代码
                num_code = StockCodeUtils.split_code(code)[0]
                df = api_func(symbol=num_code)

                if not df.empty:
                    df["stock_code"] = code
                    all_data.append(df)
            except Exception as e:
                logger.warning(f"获取{code} {report_type}财务报告失败：{e}")
                continue

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 转换日期格式 - AKShare已经是datetime格式
        if "report_date" in result_df.columns:
            result_df["end_date"] = pd.to_datetime(result_df["report_date"])
        if "announce_date" in result_df.columns:
            result_df["ann_date"] = pd.to_datetime(result_df["announce_date"])

        # 添加report_type
        result_df["report_type"] = report_type

        # 数据校验
        required_cols = ["stock_code"]
        if "end_date" in result_df.columns:
            required_cols.append("end_date")
        if self.validate_data(result_df, required_columns=required_cols):
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
        all_data = []

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        for code in stock_codes:
            try:
                self._rate_limit_check()

                # AKShare获取财务指标数据
                num_code = StockCodeUtils.split_code(code)[0]
                df = ak.stock_financial_analysis_indicator(symbol=num_code)

                if not df.empty:
                    # 按日期范围筛选
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"])
                        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

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
        if "date" in result_df.columns:
            result_df["end_date"] = pd.to_datetime(result_df["date"])

        # 重命名关键指标字段（保持接口标准化）
        rename_map = {
            "净资产收益率": "roe",
            "总资产净利润率": "roa",
            "销售毛利率": "gross_margin",
            "销售净利率": "net_margin",
            "资产负债率": "debt_ratio",
            "流动比率": "current_ratio",
            "速动比率": "quick_ratio",
            "每股收益": "eps",
            "每股净资产": "bvps",
        }

        for old_name, new_name in rename_map.items():
            if old_name in result_df.columns:
                result_df = result_df.rename(columns={old_name: new_name})

        # 保留标准字段
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
        required_cols = ["stock_code"]
        if "end_date" in result_df.columns:
            required_cols.append("end_date")
        if self.validate_data(result_df, required_columns=required_cols):
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
        all_data = []

        for code in stock_codes:
            try:
                self._rate_limit_check()

                # AKShare获取分红送配数据
                num_code = StockCodeUtils.split_code(code)[0]
                df = ak.stock_history_dividend(symbol=num_code)

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
        date_columns = {"ex_dividend_date": "ex_date", "record_date": "record_date", "pay_date": "pay_date"}

        for col in date_columns:
            if col in result_df.columns:
                result_df[date_columns[col]] = pd.to_datetime(result_df[col], errors="coerce")

        # 重命名字段
        if "cash_dividend" in result_df.columns:
            result_df = result_df.rename(columns={"cash_dividend": "dividend_per_share"})
        if "stock_dividend" in result_df.columns:
            result_df = result_df.rename(columns={"stock_dividend": "bonus_ratio"})

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

        # AKShare获取融资融券数据，分别获取上证和深证然后合并
        try:
            df_sh = ak.stock_margin_sse()
            df_sz = ak.stock_margin_szse()
            df = pd.concat([df_sh, df_sz], ignore_index=True)

            if df.empty:
                logger.warning("AKShare返回融资融券数据为空")
                return pd.DataFrame()

            # 转换日期格式
            df["trade_date"] = pd.to_datetime(df["信用交易日期"], format="%Y%m%d")

            # 按日期范围筛选
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df["trade_date"] >= start_dt) & (df["trade_date"] <= end_dt)]

            # 重命名字段（AKShare返回中文列名）
            df = df.rename(
                columns={
                    "融资余额": "margin_balance",
                    "融券余量": "short_balance",
                    "融资买入额": "margin_buy",
                }
            )

            # 如果有具体股票代码，可以筛选
            # AKShare只提供汇总数据，不提供单只股票，这里保持原样
            if stock_codes:
                logger.warning("AKShare融资融券接口只提供汇总数据，不支持单只股票查询")

            all_data = [df]

        except Exception as e:
            logger.error(f"获取融资融券数据失败：{e}")
            return pd.DataFrame()

        if not all_data or all_data[0].empty:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)

        # 保留需要的字段
        required_columns = ["trade_date", "margin_balance", "margin_buy", "short_balance"]

        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = None

        # AKShare不提供单只股票数据
        result_df["stock_code"] = None

        result_df = result_df[["stock_code"] + required_columns].copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["trade_date"]):
            return result_df
        return pd.DataFrame()
