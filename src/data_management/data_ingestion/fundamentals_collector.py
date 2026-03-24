"""
基本面数据采集器基类
所有基本面数据源都需要继承此基类，实现统一接口
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class FundamentalsCollector(ABC):
    """基本面数据采集器基类"""

    def __init__(self, source: str, config: Dict):
        self.source = source  # 数据源名称（Wind/Tushare/JoinQuant）
        self.config = config  # 采集配置
        self.priority = config.get("priority", 999)  # 优先级，数字越小优先级越高
        self.weight = config.get("weight", 1.0)  # 权重，用于负载均衡
        self.availability = 1.0  # 可用性，0-1之间
        self.avg_response_time = 0.0  # 平均响应时间（毫秒）
        self.error_count = 0  # 错误次数
        self.last_sync_time: Optional[datetime] = None
        self.last_error_time: Optional[float] = None
        self.max_retry_times = config.get("max_retry_times", 3)
        self.retry_interval = config.get("retry_interval", 1)  # 重试间隔（秒）

    @abstractmethod
    def get_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        """
        获取股票列表基本信息
        Args:
            list_status: 上市状态 L-上市，D-退市，P-暂停上市
        Returns:
            包含股票基本信息的DataFrame，字段：
            stock_code, name, fullname, enname, industry, industry_code,
            market, list_date, delist_date, is_hs, curr_type
        """
        pass

    @abstractmethod
    def get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取每日基本面指标（市值、换手率、PE、PB等）
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含每日基本面的DataFrame，字段：
            stock_code, trade_date, total_share, float_share, total_mv,
            circ_mv, pe, pb, turnover_rate, volume_ratio
        """
        pass

    @abstractmethod
    def get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        """
        获取财务报告（资产负债表、利润表、现金流量表）
        Args:
            stock_codes: 股票代码列表
            report_type: 报告类型 'income'利润表, 'balance'资产负债表, 'cashflow'现金流量表
        Returns:
            包含财务报告数据的DataFrame
        """
        pass

    @abstractmethod
    def get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取财务指标（ROE、ROA、毛利率、净利率等）
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含财务指标的DataFrame，字段：
            stock_code, end_date, roe, roa, gross_margin, net_margin,
            debt_ratio, current_ratio, quick_ratio, eps, bvps
        """
        pass

    @abstractmethod
    def get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取分红送股数据
        Args:
            stock_codes: 股票代码列表
        Returns:
            包含分红数据的DataFrame，字段：
            stock_code, dividend_date, ex_date, dividend_per_share,
            bonus_ratio, split_ratio, record_date, pay_date
        """
        pass

    @abstractmethod
    def get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取融资融券数据
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        Returns:
            包含融资融券数据的DataFrame，字段：
            stock_code, trade_date, margin_balance, margin_buy,
            margin_loan, short_sell, short_balance, interest_rate
        """
        pass

    def validate_data(self, df: pd.DataFrame, required_columns: List[str] = None) -> bool:
        """
        数据有效性校验
        Args:
            df: 待校验的数据
            required_columns: 必须的字段列表
        Returns:
            是否有效
        """
        if df is None or df.empty:
            logger.warning(f"[{self.source}] 采集的数据为空")
            return False

        required_columns = required_columns or ["stock_code"]
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"[{self.source}] 采集的数据缺少必要字段：{col}")
                return False

        return True

    def record_success(self, response_time: float):
        """
        记录成功请求
        Args:
            response_time: 响应时间（毫秒）
        """
        self.error_count = max(0, self.error_count - 1)
        # 滑动平均计算响应时间
        self.avg_response_time = self.avg_response_time * 0.7 + response_time * 0.3
        # 更新可用性
        self.availability = min(1.0, self.availability + 0.1)
        self.last_sync_time = DateTimeUtils.now()
        logger.debug(f"[{self.source}] 请求成功，响应时间：{response_time:.2f}ms，可用性：{self.availability:.2f}")

    def record_error(self, error_msg: str = ""):
        """
        记录失败请求
        Args:
            error_msg: 错误信息
        """
        self.error_count += 1
        self.last_error_time = time.time()
        # 可用性下降
        self.availability = max(0.0, self.availability - 0.3)
        logger.error(
            f"[{self.source}] 请求失败，错误：{error_msg}，错误次数：{self.error_count}，可用性：{self.availability:.2f}"
        )

    def is_available(self) -> bool:
        """
        判断数据源是否可用
        Returns:
            是否可用
        """
        # 连续错误超过5次，暂停使用5分钟
        if self.error_count >= 5 and self.last_error_time:
            if time.time() - self.last_error_time < 300:
                return False
        return self.availability > 0.3

    def execute_with_retry(self, func, *args, **kwargs):
        """
        带重试的执行
        Args:
            func: 要执行的函数
            *args: 参数
            **kwargs: 关键字参数
        Returns:
            执行结果
        """
        for retry in range(self.max_retry_times):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000
                self.record_success(response_time)
                return result
            except Exception as e:
                self.record_error(str(e))
                if retry < self.max_retry_times - 1:
                    time.sleep(self.retry_interval * (retry + 1))  # 指数退避
                    logger.info(f"[{self.source}] 第{retry+1}次重试")
                else:
                    logger.error(f"[{self.source}] 重试{self.max_retry_times}次全部失败")
                    raise

    def get_source_info(self) -> Dict:
        """
        获取数据源信息
        Returns:
            数据源信息字典
        """
        return {
            "source": self.source,
            "priority": self.priority,
            "weight": self.weight,
            "availability": self.availability,
            "avg_response_time": self.avg_response_time,
            "error_count": self.error_count,
            "is_available": self.is_available(),
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
        }
