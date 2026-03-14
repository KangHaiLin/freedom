"""
公共工具类单元测试
"""
import pytest
from datetime import datetime, date
import pandas as pd

from common.utils import DateTimeUtils, NumberUtils, StockCodeUtils, CryptoUtils
from common.constants import BusinessConstants


class TestDateTimeUtils:
    """日期时间工具类测试"""

    def test_parse(self):
        """测试日期解析"""
        # 字符串解析
        dt = DateTimeUtils.parse("2023-01-01")
        assert isinstance(dt, datetime)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1

        # datetime对象直接返回
        dt2 = datetime(2023, 1, 1)
        assert DateTimeUtils.parse(dt2) == dt2

        # date对象转换
        d = date(2023, 1, 1)
        dt3 = DateTimeUtils.parse(d)
        assert isinstance(dt3, datetime)
        assert dt3.date() == d

    def test_to_str(self):
        """测试日期转字符串"""
        dt = datetime(2023, 1, 1, 12, 34, 56)
        assert DateTimeUtils.to_str(dt) == "2023-01-01 12:34:56"
        assert DateTimeUtils.to_str(dt, format="%Y-%m-%d") == "2023-01-01"

    def test_now(self):
        """测试获取当前时间"""
        now = DateTimeUtils.now()
        assert isinstance(now, datetime)
        assert (datetime.now() - now).total_seconds() < 1

    def test_now_str(self):
        """测试获取当前时间字符串"""
        now_str = DateTimeUtils.now_str()
        assert isinstance(now_str, str)
        assert len(now_str) == 19  # YYYY-MM-DD HH:MM:SS

    def test_is_trading_day(self):
        """测试是否为交易日"""
        # 2023-01-01是周日，非交易日
        assert not DateTimeUtils.is_trading_day(date(2023, 1, 1))
        # 2023-01-03是周二，交易日
        assert DateTimeUtils.is_trading_day(date(2023, 1, 3))


class TestNumberUtils:
    """数字工具类测试"""

    def test_round_price(self):
        """测试价格四舍五入"""
        assert NumberUtils.round_price(10.123) == 10.12
        assert NumberUtils.round_price(10.126) == 10.13
        assert NumberUtils.round_price(10.0) == 10.00

    def test_round_ratio(self):
        """测试比率四舍五入"""
        assert NumberUtils.round_ratio(1.1234) == 1.1234
        assert NumberUtils.round_ratio(1.12345) == 1.1235

    def test_format_percent(self):
        """测试百分比格式化"""
        assert NumberUtils.format_percent(0.1234) == "12.34%"
        assert NumberUtils.format_percent(1.234) == "123.40%"

    def test_is_number(self):
        """测试是否为数字"""
        assert NumberUtils.is_number(123)
        assert NumberUtils.is_number(123.45)
        assert NumberUtils.is_number("123.45")
        assert not NumberUtils.is_number("abc")


class TestStockCodeUtils:
    """股票代码工具类测试"""

    def test_normalize_code(self):
        """测试股票代码标准化"""
        assert StockCodeUtils.normalize_code("000001") == "000001.SZ"
        assert StockCodeUtils.normalize_code("600000") == "600000.SH"
        assert StockCodeUtils.normalize_code("830000") == "830000.BJ"
        assert StockCodeUtils.normalize_code("000001.SZ") == "000001.SZ"
        assert StockCodeUtils.normalize_code("000001.XSHE") == "000001.SZ"

    def test_split_code(self):
        """测试拆分股票代码"""
        num, exchange = StockCodeUtils.split_code("000001.SZ")
        assert num == "000001"
        assert exchange == StockCodeUtils.EXCHANGE_SZ

        num, exchange = StockCodeUtils.split_code("600000.SH")
        assert num == "600000"
        assert exchange == StockCodeUtils.EXCHANGE_SH

    def test_get_exchange(self):
        """测试获取交易所"""
        assert StockCodeUtils.get_exchange("000001.SZ") == StockCodeUtils.EXCHANGE_SZ
        assert StockCodeUtils.get_exchange("600000") == StockCodeUtils.EXCHANGE_SH

    def test_is_valid_code(self):
        """测试是否为有效股票代码"""
        assert StockCodeUtils.is_valid_code("000001.SZ")
        assert StockCodeUtils.is_valid_code("600000.SH")
        assert not StockCodeUtils.is_valid_code("123456")
        assert not StockCodeUtils.is_valid_code("00000.XX")

    def test_get_price_limit(self):
        """测试获取涨跌幅限制"""
        # 主板
        assert StockCodeUtils.get_price_limit("000001.SZ") == 0.1
        assert StockCodeUtils.get_price_limit("600000.SH") == 0.1
        # 创业板
        assert StockCodeUtils.get_price_limit("300001.SZ") == 0.2
        # 科创板
        assert StockCodeUtils.get_price_limit("688001.SH") == 0.2
        # 北交所
        assert StockCodeUtils.get_price_limit("830001.BJ") == 0.3


class TestCryptoUtils:
    """加密工具类测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test123456"
        hashed = CryptoUtils.hash_password(password)
        assert hashed != password
        assert CryptoUtils.verify_password(password, hashed)
        assert not CryptoUtils.verify_password("wrongpass", hashed)

    def test_api_key(self):
        """测试API Key生成和验证"""
        api_key = CryptoUtils.generate_api_key()
        assert len(api_key) == 32
        assert CryptoUtils.verify_api_key(api_key)
        assert not CryptoUtils.verify_api_key("invalid_key")

    def test_jwt_token(self):
        """测试JWT令牌生成和验证"""
        payload = {"user_id": 1, "username": "test"}
        token = CryptoUtils.generate_jwt_token(payload, expires_in=3600)
        assert token is not None
        decoded = CryptoUtils.verify_jwt_token(token)
        assert decoded["user_id"] == 1
        assert decoded["username"] == "test"

        # 测试过期令牌
        expired_token = CryptoUtils.generate_jwt_token(payload, expires_in=-1)
        with pytest.raises(Exception):
            CryptoUtils.verify_jwt_token(expired_token)

    def test_hmac_sign(self):
        """测试HMAC签名"""
        data = "test data"
        secret = "test_secret"
        sign = CryptoUtils.hmac_sign(data, secret)
        assert sign is not None
        assert CryptoUtils.verify_hmac_sign(data, sign, secret)
        assert not CryptoUtils.verify_hmac_sign(data, "wrong_sign", secret)
