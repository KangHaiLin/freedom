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

    def test_now(self):
        """测试获取当前时间"""
        now = DateTimeUtils.now()
        assert isinstance(now, datetime)
        # 带时区的时间比较
        now_naive = datetime.now()
        now_aware = DateTimeUtils.SH_TZ.localize(now_naive)
        assert (now_aware - now).total_seconds() < 1

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


import decimal
class TestNumberUtils:
    """数字工具类测试"""

    def test_round_price(self):
        """测试价格四舍五入"""
        assert NumberUtils.round_price(10.123) == decimal.Decimal('10.12')
        assert NumberUtils.round_price(10.126) == decimal.Decimal('10.13')
        assert NumberUtils.round_price(10.0) == decimal.Decimal('10.00')

    def test_round_ratio(self):
        """测试比率四舍五入"""
        assert NumberUtils.round_ratio(1.1234) == decimal.Decimal('1.1234')
        assert NumberUtils.round_ratio(1.12345) == decimal.Decimal('1.1235')

    def test_format_percent(self):
        """测试百分比格式化"""
        assert NumberUtils.format_percent(0.1234) == "12.34%"
        assert NumberUtils.format_percent(1.234) == "123.40%"


class TestStockCodeUtils:
    """股票代码工具类测试"""

    def test_normalize_code(self):
        """测试股票代码标准化"""
        assert StockCodeUtils.normalize_code("000001") == "000001.SZ"
        assert StockCodeUtils.normalize_code("600000") == "600000.SH"
        assert StockCodeUtils.normalize_code("830000") == "830000.BJ"
        assert StockCodeUtils.normalize_code("000001.SZ") == "000001.SZ"
        assert StockCodeUtils.normalize_code("000001.sz") == "000001.SZ"

    def test_split_code(self):
        """测试拆分股票代码"""
        num, exchange = StockCodeUtils.split_code("000001.SZ")
        assert num == "000001"
        assert exchange == StockCodeUtils.EXCHANGE_SZ

        num, exchange = StockCodeUtils.split_code("600000.SH")
        assert num == "600000"
        assert exchange == StockCodeUtils.EXCHANGE_SH

    def test_guess_exchange(self):
        """测试猜测交易所"""
        assert StockCodeUtils.guess_exchange("000001") == StockCodeUtils.EXCHANGE_SZ
        assert StockCodeUtils.guess_exchange("600000") == StockCodeUtils.EXCHANGE_SH
        assert StockCodeUtils.guess_exchange("830000") == StockCodeUtils.EXCHANGE_BJ

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
        hashed, salt = CryptoUtils.hash_password(password)
        assert hashed != password
        assert CryptoUtils.verify_password(password, hashed, salt)
        assert not CryptoUtils.verify_password("wrongpass", hashed, salt)

    def test_api_key(self):
        """测试API Key生成"""
        api_key, api_secret = CryptoUtils.generate_api_key()
        assert len(api_key) == 34  # AK + 32位hex
        assert len(api_secret) == 64  # 32*2位hex
        assert api_key.startswith("AK")

    def test_jwt_token(self):
        """测试JWT令牌生成和验证"""
        secret_key = "test_secret_key"
        user_id = 1
        username = "test"
        role = "user"

        token = CryptoUtils.generate_jwt_token(user_id, username, role, secret_key, expire_minutes=60)
        assert token is not None

        decoded = CryptoUtils.verify_jwt_token(token, secret_key)
        assert decoded is not None
        assert decoded["user_id"] == user_id
        assert decoded["username"] == username
        assert decoded["role"] == role

    def test_hmac_signature(self):
        """测试HMAC签名"""
        params = {"key1": "value1", "key2": "value2"}
        secret = "test_secret"

        signature, timestamp, nonce = CryptoUtils.generate_hmac_signature(params, secret)
        assert signature is not None
        assert timestamp is not None
        assert nonce is not None

        # 验证签名
        assert CryptoUtils.verify_hmac_signature(signature, params, secret, timestamp, nonce)
        assert not CryptoUtils.verify_hmac_signature("wrong_sign", params, secret, timestamp, nonce)

        # 测试过期签名
        expired_timestamp = int(datetime.now().timestamp()) - 600  # 10分钟前
        signature2, _, _ = CryptoUtils.generate_hmac_signature(params, secret, timestamp=expired_timestamp)
        assert not CryptoUtils.verify_hmac_signature(signature2, params, secret, expired_timestamp, nonce)
