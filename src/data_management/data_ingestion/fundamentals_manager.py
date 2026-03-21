"""
基本面数据源管理器
动态选择最优数据源，支持多数据源自动切换、负载均衡、降级重试
"""
from typing import List, Dict, Optional
import random
import logging
import pandas as pd

from .fundamentals_collector import FundamentalsCollector
from common.exceptions import DataSourceException
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class FundamentalsManager:
    """基本面数据源管理器，支持动态选择最优数据源"""

    def __init__(self):
        self.sources: List[FundamentalsCollector] = []
        self.source_map: Dict[str, FundamentalsCollector] = {}
        self.last_source_index = 0

    def add_source(self, source: FundamentalsCollector):
        """
        添加数据源
        Args:
            source: 数据源实例
        """
        self.sources.append(source)
        self.source_map[source.source] = source
        # 按优先级排序
        self.sources.sort(key=lambda x: x.priority)
        logger.info(f"添加基本面数据源：{source.source}，当前数据源总数：{len(self.sources)}")

    def remove_source(self, source_name: str):
        """
        移除数据源
        Args:
            source_name: 数据源名称
        """
        if source_name in self.source_map:
            source = self.source_map.pop(source_name)
            self.sources.remove(source)
            logger.info(f"移除基本面数据源：{source_name}，当前数据源总数：{len(self.sources)}")

    def select_best_source(self) -> FundamentalsCollector:
        """
        选择最优数据源
        综合考虑优先级、可用性、响应时间，加权随机选择
        Returns:
            最优数据源实例
        """
        # 过滤可用数据源
        available_sources = [s for s in self.sources if s.is_available()]
        if not available_sources:
            logger.error("无可用基本面数据源")
            raise DataSourceException("无可用基本面数据源")

        # 加权随机选择，综合考虑优先级、可用性、响应时间
        def calculate_score(source: FundamentalsCollector) -> float:
            """计算数据源得分，越高越好"""
            # 优先级权重40%，可用性权重30%，响应时间权重30%
            priority_score = (10 - source.priority) * 0.4  # 优先级越高（数字越小）得分越高
            availability_score = source.availability * 10 * 0.3  # 可用性0-1转换为0-10分
            # 响应时间越短得分越高，最大10分
            response_time_score = max(0, 1000 - source.avg_response_time) / 100 * 0.3
            total_score = priority_score + availability_score + response_time_score
            logger.debug(f"基本面数据源{source.source}得分：{total_score:.2f}，优先级={source.priority}，可用性={source.availability:.2f}，响应时间={source.avg_response_time:.2f}ms")
            return total_score

        # 按分数排序，选择前3个加权随机
        available_sources.sort(key=calculate_score, reverse=True)
        top_sources = available_sources[:3]

        # 加权随机
        total_weight = sum(s.weight for s in top_sources)
        r = random.uniform(0, total_weight)
        current_weight = 0
        for source in top_sources:
            current_weight += source.weight
            if r <= current_weight:
                logger.debug(f"选择基本面数据源：{source.source}")
                return source
        return top_sources[0]

    def execute_query(self, query_func: str, *args, **kwargs) -> pd.DataFrame:
        """
        执行查询，自动降级重试
        Args:
            query_func: 要执行的查询方法名，如'get_stock_basic'
            *args: 参数
            **kwargs: 关键字参数
        Returns:
            查询结果DataFrame
        """
        max_retries = len(self.sources)
        tried_sources = []

        for _ in range(max_retries):
            try:
                source = self.select_best_source()
                if source.source in tried_sources:
                    continue  # 跳过已经尝试过的数据源
                tried_sources.append(source.source)

                logger.debug(f"使用基本面数据源{source.source}执行查询：{query_func}")
                result = getattr(source, query_func)(*args, **kwargs)

                if not result.empty:
                    logger.debug(f"基本面数据源{source.source}查询成功，返回{len(result)}条数据")
                    return result
                else:
                    logger.warning(f"基本面数据源{source.source}返回数据为空，尝试下一个数据源")
                    source.record_error("返回数据为空")

            except Exception as e:
                logger.error(f"基本面数据源查询失败：{e}")
                continue

        logger.error(f"所有基本面数据源均不可用，尝试了{len(tried_sources)}个数据源")
        raise DataSourceException("所有基本面数据源均不可用")

    def get_stock_basic(self, list_status: str = 'L') -> pd.DataFrame:
        """
        获取股票列表基本信息
        Args:
            list_status: 上市状态
        Returns:
            股票基本信息DataFrame
        """
        return self.execute_query('get_stock_basic', list_status)

    def get_daily_basic(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取每日基本面指标
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            每日基本面DataFrame
        """
        return self.execute_query('get_daily_basic', stock_codes, start_date, end_date)

    def get_financial_report(self, stock_codes: List[str], report_type: str) -> pd.DataFrame:
        """
        获取财务报告
        Args:
            stock_codes: 股票代码列表
            report_type: 报告类型
        Returns:
            财务报告DataFrame
        """
        return self.execute_query('get_financial_report', stock_codes, report_type)

    def get_financial_indicator(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取财务指标
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            财务指标DataFrame
        """
        return self.execute_query('get_financial_indicator', stock_codes, start_date, end_date)

    def get_dividend(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取分红送股数据
        Args:
            stock_codes: 股票代码列表
        Returns:
            分红数据DataFrame
        """
        return self.execute_query('get_dividend', stock_codes)

    def get_margin_trading(self, stock_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取融资融券数据
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        Returns:
            融资融券数据DataFrame
        """
        return self.execute_query('get_margin_trading', stock_codes, start_date, end_date)

    def get_source_status(self) -> List[Dict]:
        """
        获取所有数据源状态
        Returns:
            数据源状态列表
        """
        return [s.get_source_info() for s in self.sources]

    def get_available_source_count(self) -> int:
        """
        获取可用数据源数量
        Returns:
            可用数据源数量
        """
        return sum(1 for s in self.sources if s.is_available())

    def get_source_by_name(self, source_name: str) -> Optional[FundamentalsCollector]:
        """
        根据名称获取数据源
        Args:
            source_name: 数据源名称
        Returns:
            数据源实例，不存在返回None
        """
        return self.source_map.get(source_name)

    def health_check(self) -> Dict:
        """
        数据源健康检查
        Returns:
            健康检查结果
        """
        available_count = self.get_available_source_count()
        total_count = len(self.sources)
        health_status = {
            "total_sources": total_count,
            "available_sources": available_count,
            "health_score": available_count / total_count if total_count > 0 else 0,
            "sources": self.get_source_status(),
            "check_time": DateTimeUtils.now_str()
        }
        logger.info(f"基本面数据源健康检查：可用{available_count}/{total_count}个，健康得分：{health_status['health_score']:.2f}")
        return health_status


# 全局基本面数据源管理器实例
fundamentals_manager = FundamentalsManager()
