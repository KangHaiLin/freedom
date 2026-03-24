"""
日期时间工具类
提供A股交易相关的日期时间处理功能
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Union

import holidays
import pytz


class DateTimeUtils:
    """日期时间工具类"""

    SH_TZ = pytz.timezone("Asia/Shanghai")
    UTC_TZ = pytz.UTC

    # A股节假日数据（可动态更新）
    _cn_holidays = holidays.CN()

    @classmethod
    def now(cls) -> datetime:
        """获取当前上海时间"""
        return datetime.now(cls.SH_TZ)

    @classmethod
    def now_str(cls, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """获取当前时间字符串"""
        return cls.now().strftime(format_str)

    @classmethod
    def today(cls) -> date:
        """获取当前日期"""
        return cls.now().date()

    @classmethod
    def today_str(cls, format_str: str = "%Y-%m-%d") -> str:
        """获取当前日期字符串"""
        return cls.today().strftime(format_str)

    @classmethod
    def to_str(cls, dt: Union[datetime, date, str], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """将日期时间对象转换为字符串，如果已经是字符串直接返回"""
        if isinstance(dt, str):
            return dt
        if isinstance(dt, date):
            return dt.strftime("%Y-%m-%d")
        return dt.strftime(format_str)

    @classmethod
    def is_trading_day(cls, dt: Union[date, str]) -> bool:
        """判断是否是A股交易日"""
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d").date()

        # 周末不是交易日
        if dt.weekday() >= 5:
            return False

        # 节假日不是交易日
        if dt in cls._cn_holidays:
            return False

        return True

    @classmethod
    def get_trading_days(cls, start_date: str, end_date: str) -> List[date]:
        """获取指定日期范围内的交易日列表"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        days = []
        current = start
        while current <= end:
            if cls.is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    @classmethod
    def get_previous_trading_day(cls, dt: Union[date, str] = None) -> date:
        """获取上一个交易日"""
        if dt is None:
            dt = cls.today()
        elif isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d").date()

        current = dt - timedelta(days=1)
        while not cls.is_trading_day(current):
            current -= timedelta(days=1)
        return current

    @classmethod
    def get_next_trading_day(cls, dt: Union[date, str] = None) -> date:
        """获取下一个交易日"""
        if dt is None:
            dt = cls.today()
        elif isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d").date()

        current = dt + timedelta(days=1)
        while not cls.is_trading_day(current):
            current += timedelta(days=1)
        return current

    @classmethod
    def is_trading_time(cls, dt: Optional[datetime] = None) -> bool:
        """判断是否是交易时间"""
        dt = dt or cls.now()

        # 首先判断是否是交易日
        if not cls.is_trading_day(dt.date()):
            return False

        time = dt.time()

        # 早盘：9:30-11:30
        morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()

        # 午盘：13:00-15:00
        afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()

        # 集合竞价时间：9:15-9:25
        call_auction_start = datetime.strptime("09:15:00", "%H:%M:%S").time()
        call_auction_end = datetime.strptime("09:25:00", "%H:%M:%S").time()

        return (
            (call_auction_start <= time <= call_auction_end)
            or (morning_start <= time <= morning_end)
            or (afternoon_start <= time <= afternoon_end)
        )

    @classmethod
    def is_market_open(cls) -> bool:
        """判断当前市场是否开盘"""
        return cls.is_trading_time()

    @classmethod
    def get_trading_session(cls, dt: Optional[datetime] = None) -> str:
        """获取当前交易时段"""
        dt = dt or cls.now()
        time = dt.time()

        call_auction_start = datetime.strptime("09:15:00", "%H:%M:%S").time()
        call_auction_end = datetime.strptime("09:25:00", "%H:%M:%S").time()
        morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
        afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()

        if call_auction_start <= time <= call_auction_end:
            return "call_auction"
        elif morning_start <= time <= morning_end:
            return "morning_session"
        elif time > morning_end and time < afternoon_start:
            return "midday_break"
        elif afternoon_start <= time <= afternoon_end:
            return "afternoon_session"
        else:
            return "closed"

    @classmethod
    def to_shanghai_time(cls, dt: datetime) -> datetime:
        """转换为上海时区时间"""
        if dt.tzinfo is None:
            dt = cls.UTC_TZ.localize(dt)
        return dt.astimezone(cls.SH_TZ)

    @classmethod
    def to_utc_time(cls, dt: datetime) -> datetime:
        """转换为UTC时间"""
        if dt.tzinfo is None:
            dt = cls.SH_TZ.localize(dt)
        return dt.astimezone(cls.UTC_TZ)

    @classmethod
    def calculate_trading_minutes(cls, start_time: datetime, end_time: datetime) -> int:
        """计算两个时间之间的交易分钟数"""
        minutes = 0
        current = start_time.replace(second=0, microsecond=0)
        end = end_time.replace(second=0, microsecond=0)

        while current < end:
            if cls.is_trading_time(current):
                minutes += 1
            current += timedelta(minutes=1)

        return minutes

    @classmethod
    def update_holidays(cls, holiday_list: List[date]):
        """更新节假日数据"""
        for holiday in holiday_list:
            cls._cn_holidays.append(holiday)

    @classmethod
    def parse(cls, dt: Union[str, date, datetime]) -> datetime:
        """解析日期时间，支持多种输入格式"""
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, date):
            return datetime.combine(dt, datetime.min.time())
        if isinstance(dt, str):
            # 尝试多种格式解析
            formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
            for fmt in formats:
                try:
                    return datetime.strptime(dt, fmt)
                except ValueError:
                    continue
            raise ValueError(f"无法解析日期时间：{dt}，支持格式：YYYY-MM-DD[ HH:MM[:SS]]")
