"""
历史数据自动同步任务
实现全量获取+增量更新自动同步功能
- 第一次运行：全量获取从2020-01-01到今天的历史数据
- 后续运行：自动检测增量，只获取新增数据
- 股票过滤：只同步当前未退市且非ST的股票
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional, Tuple
from abc import ABC
import logging

from system_management.task_scheduler.base_task import BaseTask, TaskResult
from data_management.data_ingestion import AKShareCollector, AKShareFundamentalsCollector
from data_management.data_storage import storage_manager, ClickHouseStorage
from common.config import settings
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class DataFrequency:
    """数据频率枚举"""
    DAILY = "daily"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    MINUTE_60 = "60min"
    TICK = "tick"


class SyncResult:
    """同步结果"""
    def __init__(
        self,
        success: bool,
        total_stocks: int = 0,
        success_stocks: int = 0,
        failed_stocks: int = 0,
        total_records: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        message: str = "",
    ):
        self.success = success
        self.total_stocks = total_stocks
        self.success_stocks = success_stocks
        self.failed_stocks = failed_stocks
        self.total_records = total_records
        self.start_date = start_date
        self.end_date = end_date
        self.message = message
        self.sync_time = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "total_stocks": self.total_stocks,
            "success_stocks": self.success_stocks,
            "failed_stocks": self.failed_stocks,
            "total_records": self.total_records,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "message": self.message,
            "sync_time": self.sync_time.isoformat(),
            "duration_seconds": self.sync_time.timestamp() - datetime.now().timestamp(),
        }


class HistoricalSyncTask(BaseTask, ABC):
    """历史数据自动同步任务基类

    自动检测增量：
    - 如果数据库为空 → 执行全量同步从默认起始日期到今天
    - 如果数据库有数据 → 从最新日期的下一个交易日开始同步到今天
    - 如果没有新的交易日 → 不需要同步直接返回
    """

    # 表名映射
    TABLE_NAME_MAP = {
        DataFrequency.DAILY: "daily_market_data",
        DataFrequency.MINUTE_1: "minute1_market_data",
        DataFrequency.MINUTE_5: "minute5_market_data",
        DataFrequency.MINUTE_15: "minute15_market_data",
        DataFrequency.MINUTE_30: "minute30_market_data",
        DataFrequency.MINUTE_60: "minute60_market_data",
        DataFrequency.TICK: "tick_market_data",
    }

    def __init__(
        self,
        frequency: str,
        task_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        default_start_date: Optional[str] = None,
        max_retries: Optional[int] = None,
        filter_only_listed: Optional[bool] = None,
        filter_exclude_st: Optional[bool] = None,
    ):
        """
        初始化同步任务

        Args:
            frequency: 数据频率 daily/1min/5min/.../tick
            task_name: 任务名称
            batch_size: 每批处理股票数量
            default_start_date: 全量同步默认起始日期 (YYYY-MM-DD)
            max_retries: 最大重试次数
            filter_only_listed: 是否只保留未退市股票
            filter_exclude_st: 是否排除ST股票
        """
        self.frequency = frequency
        task_name = task_name or f"HistoricalSync_{frequency}"
        super().__init__(task_name)

        # 从配置读取默认值，允许覆盖
        self.batch_size = batch_size or getattr(settings, "SYNC_BATCH_SIZE", 10)
        self.max_retries = max_retries or getattr(settings, "SYNC_MAX_RETRIES", 3)
        self.default_start_date = default_start_date or getattr(
            settings, "SYNC_DEFAULT_START_DATE", "2020-01-01"
        )
        self.filter_only_listed = (
            filter_only_listed
            if filter_only_listed is not None
            else getattr(settings, "FILTER_ONLY_LISTED", True)
        )
        self.filter_exclude_st = (
            filter_exclude_st
            if filter_exclude_st is not None
            else getattr(settings, "FILTER_EXCLUDE_ST", True)
        )

        # 表名
        self.table_name = self.TABLE_NAME_MAP.get(frequency, f"{frequency}_market_data")

        # 初始化采集器
        self.collector = AKShareCollector({})
        self.fundamentals_collector = AKShareFundamentalsCollector({})

        # 获取ClickHouse存储
        self.storage = storage_manager.get_storage_by_type("clickhouse")
        if not self.storage:
            raise RuntimeError("ClickHouse存储未找到")

        self.clickhouse_storage: ClickHouseStorage = self.storage

    def get_latest_trade_date(self) -> Optional[datetime]:
        """
        查询数据库中最新的交易日期

        Returns:
            最新交易日期，如果表不存在或为空返回None
        """
        try:
            if not self.clickhouse_storage.table_exists(self.table_name):
                logger.info(f"表{self.table_name}不存在，需要全量同步")
                return None

            # 查询最大交易日期
            sql = f"SELECT MAX(trade_date) FROM {self.table_name}"
            result = self.clickhouse_storage.execute_sql(sql)

            if result and len(result) > 0 and len(result[0]) > 0:
                latest_date = result[0][0]
                if latest_date:
                    if isinstance(latest_date, datetime):
                        return latest_date
                    elif isinstance(latest_date, str):
                        return datetime.strptime(latest_date, "%Y-%m-%d")
                    elif pd.isna(latest_date):
                        return None

            return None

        except Exception as e:
            logger.warning(f"查询最新交易日期失败：{e}，将执行全量同步")
            return None

    def find_next_trading_day(self, after_date: datetime) -> Optional[datetime]:
        """
        找到after_date之后的第一个交易日

        使用AKShare的交易日历查询

        Args:
            after_date: 在这个日期之后

        Returns:
            第一个交易日，如果没有返回None
        """
        try:
            # 获取最近一年的交易日历
            start_cal = (after_date - timedelta(days=10)).strftime("%Y%m%d")
            end_cal = datetime.now().strftime("%Y%m%d")

            calendar_df = ak.tool_trade_date_hist_sina()

            if calendar_df.empty:
                logger.warning("获取交易日历失败，使用简单跳过周末算法")
                # 简单算法：直接加1天，跳过周末
                next_day = after_date + timedelta(days=1)
                while next_day.weekday() >= 5:  # 5=周六, 6=周日
                    next_day += timedelta(days=1)
                return next_day

            # 转换日期格式
            calendar_df["trade_date"] = pd.to_datetime(calendar_df["trade_date"])

            # 过滤出after_date之后的日期
            future_dates = calendar_df[calendar_df["trade_date"] > after_date]

            if future_dates.empty:
                return None

            # 返回最早的一个
            return future_dates["trade_date"].min()

        except Exception as e:
            logger.warning(f"查找下一个交易日失败：{e}，使用简单算法")
            # 简单算法：直接加1天，跳过周末
            next_day = after_date + timedelta(days=1)
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            return next_day

    def calculate_sync_range(self) -> Optional[Tuple[datetime, datetime]]:
        """
        计算需要同步的日期范围

        逻辑：
        1. 如果数据库为空 OR 全量同步未完成（最新日期距离开始日期不足一年）→ 从头开始全量同步
        2. 如果全量同步已完成 → 增量同步

        Returns:
            (start_date, end_date) 如果需要同步，否则返回None表示不需要同步
        """
        today = datetime.now()
        default_start = datetime.strptime(self.default_start_date, "%Y-%m-%d")
        latest_date = self.get_latest_trade_date()

        # 如果没有数据 OR 全量同步未完成 → 从头全量同步
        if latest_date is None or (latest_date - default_start).days < 365:
            # 数据库为空或数据很少，说明全量同步未完成 → 从头全量同步
            start_date = default_start
            if latest_date is None:
                logger.info(f"数据库为空，执行全量同步：{start_date.date()} → {today.date()}")
            else:
                logger.info(
                    f"检测到全量同步未完成（最新日期{latest_date.date()}距离起始日期不足一年），"
                    f"从头执行全量同步：{start_date.date()} → {today.date()}"
                )
            return (start_date, today)

        # 全量同步已完成，找下一个交易日增量更新
        next_trading_day = self.find_next_trading_day(latest_date)

        if next_trading_day is None:
            logger.info(f"没有找到新的交易日，最新数据已是{latest_date.date()}，无需同步")
            return None

        if next_trading_day > today:
            logger.info(f"下一个交易日{next_trading_day.date()}在今天之后，无需同步")
            return None

        logger.info(
            f"检测到增量数据，最新日期{latest_date.date()}，需要同步从{next_trading_day.date()} → {today.date()}"
        )
        return (next_trading_day, today)

    def get_filtered_stock_list(self) -> List[str]:
        """
        获取过滤后的股票列表

        根据配置：
        - 只保留未退市股票
        - 排除ST股票

        Returns:
            股票代码列表
        """
        try:
            # 通过AKShare获取股票实时信息来过滤
            stock_info = ak.stock_zh_a_spot()

            if stock_info.empty:
                logger.warning("获取实时股票信息失败，使用基础股票列表")
                # 使用基础列表
                basic_df = self.fundamentals_collector.get_stock_basic(list_status="L")
                return basic_df["stock_code"].tolist()

            # 过滤ST股票：名称中包含"ST"
            if self.filter_exclude_st:
                stock_info = stock_info[~stock_info["名称"].str.contains("ST")]

            # AKShare的stock_zh_a_spot只返回当前上市的股票
            # 所以filter_only_listed默认已经满足

            # 转换代码格式
            def _convert_code(ak_code: str) -> str:
                # AKShare格式: sh600000 → 转换为 600000.SH
                if ak_code.startswith(("sh", "sz", "bj")):
                    prefix = ak_code[:2]
                    code = ak_code[2:]
                    if prefix == "sh":
                        return f"{code}.SH"
                    elif prefix == "sz":
                        return f"{code}.SZ"
                    elif prefix == "bj":
                        return f"{code}.BJ"
                return ak_code

            stock_info["stock_code"] = stock_info["代码"].apply(_convert_code)

            stock_list = stock_info["stock_code"].tolist()

            logger.info(f"获取过滤后股票列表完成，共{len(stock_list)}只股票")
            return stock_list

        except Exception as e:
            logger.error(f"获取过滤股票列表失败：{e}")
            # 降级：使用基础列表
            try:
                basic_df = self.fundamentals_collector.get_stock_basic(list_status="L")
                stock_list = basic_df["stock_code"].tolist()
                logger.warning(f"降级使用基础股票列表，共{len(stock_list)}只股票")
                return stock_list
            except Exception as e2:
                logger.error(f"降级获取股票列表也失败：{e2}")
                return []

    def fetch_data_batch(
        self, stock_codes: List[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        批量获取一批股票的数据

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            合并后的数据框
        """
        if self.frequency == DataFrequency.DAILY:
            return self.collector.get_daily_quote(stock_codes, start_date, end_date)
        elif self.frequency.startswith("minute") or self.frequency in [
            DataFrequency.MINUTE_1,
            DataFrequency.MINUTE_5,
            DataFrequency.MINUTE_15,
            DataFrequency.MINUTE_30,
            DataFrequency.MINUTE_60,
        ]:
            # 解析period
            period_map = {
                DataFrequency.MINUTE_1: 1,
                DataFrequency.MINUTE_5: 5,
                DataFrequency.MINUTE_15: 15,
                DataFrequency.MINUTE_30: 30,
                DataFrequency.MINUTE_60: 60,
            }
            period = period_map.get(self.frequency, 1)
            return self.collector.get_minute_quote(
                stock_codes, start_date, end_date, period
            )
        elif self.frequency == DataFrequency.TICK:
            # Tick数据按日期获取，这里只获取最后一天的数据
            # Tick数据量很大，不建议全量同步
            all_data = []
            for code in stock_codes:
                df = self.collector.get_tick_quote([code], end_date)
                if not df.empty:
                    all_data.append(df)
            if not all_data:
                return pd.DataFrame()
            return pd.concat(all_data, ignore_index=True)
        else:
            logger.error(f"不支持的数据频率：{self.frequency}")
            return pd.DataFrame()

    def write_to_database(self, df: pd.DataFrame) -> int:
        """
        写入数据到ClickHouse，利用已有去重机制

        Args:
            df: 数据框

        Returns:
            写入记录数
        """
        if df.empty:
            return 0

        # 添加created_at时间戳列（表结构要求）
        from datetime import datetime
        df['created_at'] = datetime.now()

        # 确保整数类型字段转换为整数（ClickHouse要求）
        integer_fields = ['volume']
        for field in integer_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype('Int64')

        # 确保trade_date是datetime类型
        if 'trade_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['trade_date']):
            df['trade_date'] = pd.to_datetime(df['trade_date'])

        return storage_manager.write(self.table_name, df, storage_name="clickhouse")

    def run(self) -> Any:
        """
        执行同步任务

        Returns:
            同步结果
        """
        start_time = datetime.now()
        logger.info(f"开始执行{self.frequency}数据同步任务")

        # 1. 计算需要同步的日期范围
        sync_range = self.calculate_sync_range()
        if sync_range is None:
            # 不需要同步
            result = SyncResult(
                success=True,
                message="数据已是最新，无需同步",
            )
            logger.info(f"{self.frequency}数据同步完成，无需同步新数据")
            return result.to_dict()

        start_date, end_date = sync_range
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # 2. 获取过滤后的股票列表
        stock_list = self.get_filtered_stock_list()
        if not stock_list:
            result = SyncResult(
                success=False,
                message="获取股票列表失败，同步终止",
            )
            logger.error("获取股票列表为空，同步终止")
            return result.to_dict()

        total_stocks = len(stock_list)
        success_stocks = 0
        failed_stocks = 0
        total_records = 0

        # 3. 分批处理
        for i in range(0, len(stock_list), self.batch_size):
            batch = stock_list[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(stock_list) + self.batch_size - 1) // self.batch_size

            logger.info(
                f"处理第{batch_num}/{total_batches}批，共{len(batch)}只股票"
            )

            try:
                # 获取这一批数据
                df = self.fetch_data_batch(batch, start_date_str, end_date_str)

                if not df.empty:
                    # 写入数据库
                    records_written = self.write_to_database(df)
                    total_records += records_written
                    success_stocks += len(batch)
                    logger.info(
                        f"第{batch_num}批处理完成，写入{records_written}条记录"
                    )
                else:
                    logger.warning(
                        f"第{batch_num}批未获取到数据，可能该批次没有新增数据"
                    )
                    # 空数据也算成功，因为可能确实没有新增
                    success_stocks += len(batch)

            except Exception as e:
                logger.error(f"第{batch_num}批处理失败：{e}，跳过继续处理下一批")
                failed_stocks += len(batch)
                continue

        # 4. 完成统计
        elapsed = (datetime.now() - start_time).total_seconds()
        result = SyncResult(
            success=failed_stocks == 0,
            total_stocks=total_stocks,
            success_stocks=success_stocks,
            failed_stocks=failed_stocks,
            total_records=total_records,
            start_date=start_date_str,
            end_date=end_date_str,
            message=f"同步完成，耗时{elapsed:.2f}秒，写入{total_records}条记录",
        )

        logger.info(
            f"{self.frequency}数据同步完成，"
            f"总计{total_stocks}只，成功{success_stocks}只，"
            f"失败{failed_stocks}只，写入{total_records}条记录，"
            f"耗时{elapsed:.2f}秒"
        )

        return result.to_dict()


class DailyHistoricalSyncTask(HistoricalSyncTask):
    """日线历史数据同步任务"""
    def __init__(self, **kwargs):
        super().__init__(frequency=DataFrequency.DAILY, **kwargs)


class Minute1HistoricalSyncTask(HistoricalSyncTask):
    """1分钟线历史数据同步任务"""
    def __init__(self, **kwargs):
        super().__init__(frequency=DataFrequency.MINUTE_1, **kwargs)


class Minute5HistoricalSyncTask(HistoricalSyncTask):
    """5分钟线历史数据同步任务"""
    def __init__(self, **kwargs):
        super().__init__(frequency=DataFrequency.MINUTE_5, **kwargs)


class TickHistoricalSyncTask(HistoricalSyncTask):
    """Tick数据同步任务"""
    def __init__(self, **kwargs):
        super().__init__(frequency=DataFrequency.TICK, **kwargs)
