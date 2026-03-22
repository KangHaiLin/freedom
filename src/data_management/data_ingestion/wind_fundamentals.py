"""
Wind数据源基本面数据适配器
实现Wind基本面数据接口的对接
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

# 模拟Wind API导入，实际项目中需要安装WindPy
try:
    from WindPy import w

    WIND_AVAILABLE = True
except ImportError:
    WIND_AVAILABLE = False
    logger.warning("WindPy未安装，Wind基本面数据源将无法使用")


class WindFundamentalsCollector(FundamentalsCollector):
    """Wind基本面数据采集实现"""

    def __init__(self, config: Dict):
        super().__init__("wind", config)
        if not WIND_AVAILABLE:
            raise DataSourceException("WindPy未安装，无法使用Wind基本面数据源")

        # 确保Wind已初始化
        if not w.isconnected():
            ret = w.start()
            if ret.ErrorCode != 0:
                raise DataSourceException(f"Wind连接失败，错误码：{ret.ErrorCode}")

        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit = config.get("rate_limit", 160)  # 每分钟请求次数限制

    def _rate_limit_check(self):
        """请求频率限制检查"""
        now = time.time()
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

    def get_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        """获取股票列表基本信息"""
        return self.execute_with_retry(self._get_stock_basic, list_status)

    def _get_stock_basic(self, list_status: str) -> pd.DataFrame:
        self._rate_limit_check()

        # Wind API获取股票列表
        # 使用Wind的证券基本信息接口
        error_code, data = w.wss("上市", "sec_name,fullname,industry,list_date,delist_date,exchange")
        if error_code != 0:
            logger.error(f"Wind获取股票列表失败，错误码：{error_code}")
            return pd.DataFrame()

        if not data:
            return pd.DataFrame()

        # 转换为DataFrame
        df = pd.DataFrame(data).T
        # Wind返回的数据需要根据实际格式调整，这里保持接口结构一致
        df.columns = ["stock_code", "name", "fullname", "industry", "list_date", "delist_date", "exchange"]
        df["stock_code"] = df["stock_code"].apply(lambda x: StockCodeUtils.normalize_code(x))

        # 按上市状态筛选
        # 这里根据实际情况处理，暂返回全部
        result_df = df.copy()

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "name"]):
            return result_df
        return pd.DataFrame()

    def get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取每日基本面指标"""
        return self.execute_with_retry(self._get_daily_basic, stock_codes, start_date, end_date)

    def _get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        wind_codes = [
            (
                StockCodeUtils.normalize_code(code).replace(".", ".SH")
                if code.endswith(("SH", "SH"))
                else StockCodeUtils.normalize_code(code).replace(".", ".SZ")
            )
            for code in stock_codes
        ]

        # Wind获取每日基本面数据（市值、PE、PB等）
        fields = "mkt_cap,pe,pb,turn,total_share,float_share"
        error_code, data = w.wsd(wind_codes, fields, start_date, end_date)

        if error_code != 0:
            logger.error(f"Wind获取每日基本面失败，错误码：{error_code}")
            return pd.DataFrame()

        if not data or not data.Data:
            return pd.DataFrame()

        # 转换格式，这里简化处理，实际需要根据Wind返回格式调整
        all_data = []
        for i, code in enumerate(stock_codes):
            df = pd.DataFrame(
                {
                    "stock_code": code,
                    "trade_date": data.Times,
                    "total_mv": data.Data[i][0],
                    "pe": data.Data[i][1],
                    "pb": data.Data[i][2],
                    "turnover_rate": data.Data[i][3],
                    "total_share": data.Data[i][4],
                    "float_share": data.Data[i][5],
                }
            )
            all_data.append(df)

        if not all_data:
            return pd.DataFrame()

        result_df = pd.concat(all_data, ignore_index=True)
        result_df["trade_date"] = pd.to_datetime(result_df["trade_date"])

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code", "trade_date"]):
            return result_df
        return pd.DataFrame()

    def get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        """获取财务报告"""
        return self.execute_with_retry(self._get_financial_report, stock_codes, report_type)

    def _get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        self._rate_limit_check()
        # Wind API获取财务报表
        # 具体实现依赖Wind接口，这里保持框架结构
        logger.warning("Wind财务报告获取功能待完整实现")
        return pd.DataFrame()

    def get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取财务指标"""
        return self.execute_with_retry(self._get_financial_indicator, stock_codes, start_date, end_date)

    def _get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()

        wind_codes = [
            (
                StockCodeUtils.normalize_code(code).replace(".", ".SH")
                if code.endswith(("SH", "SH"))
                else StockCodeUtils.normalize_code(code).replace(".", ".SZ")
            )
            for code in stock_codes
        ]

        # Wind获取财务指标
        fields = "roe,roa,grossmargin,netmargin,debttoassets,currentratio,quickratio,eps,bvps"
        error_code, data = w.wss(wind_codes, fields)

        if error_code != 0:
            logger.error(f"Wind获取财务指标失败，错误码：{error_code}")
            return pd.DataFrame()

        if not data or not data.Data:
            return pd.DataFrame()

        # 转换结果
        result_data = []
        for i, code in enumerate(stock_codes):
            row = {
                "stock_code": code,
                "roe": data.Data[i][0] if len(data.Data[i]) > 0 else None,
                "roa": data.Data[i][1] if len(data.Data[i]) > 1 else None,
                "gross_margin": data.Data[i][2] if len(data.Data[i]) > 2 else None,
                "net_margin": data.Data[i][3] if len(data.Data[i]) > 3 else None,
                "debt_ratio": data.Data[i][4] if len(data.Data[i]) > 4 else None,
                "current_ratio": data.Data[i][5] if len(data.Data[i]) > 5 else None,
                "quick_ratio": data.Data[i][6] if len(data.Data[i]) > 6 else None,
                "eps": data.Data[i][7] if len(data.Data[i]) > 7 else None,
                "bvps": data.Data[i][8] if len(data.Data[i]) > 8 else None,
            }
            result_data.append(row)

        result_df = pd.DataFrame(result_data)

        # 数据校验
        if self.validate_data(result_df, required_columns=["stock_code"]):
            return result_df
        return pd.DataFrame()

    def get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        """获取分红送股数据"""
        return self.execute_with_retry(self._get_dividend, stock_codes)

    def _get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        self._rate_limit_check()
        logger.warning("Wind分红数据获取功能待完整实现")
        return pd.DataFrame()

    def get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取融资融券数据"""
        return self.execute_with_retry(self._get_margin_trading, stock_codes, start_date, end_date)

    def _get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        self._rate_limit_check()
        logger.warning("Wind融资融券数据获取功能待完整实现")
        return pd.DataFrame()
