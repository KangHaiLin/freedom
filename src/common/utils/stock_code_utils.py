"""
股票代码工具类
提供A股股票代码格式化、校验、交易所识别等功能
"""

import re
from typing import Dict, Optional, Tuple


class StockCodeUtils:
    """股票代码处理工具类"""

    EXCHANGE_SH = "SH"
    EXCHANGE_SZ = "SZ"
    EXCHANGE_BJ = "BJ"

    EXCHANGE_NAMES = {EXCHANGE_SH: "上海证券交易所", EXCHANGE_SZ: "深圳证券交易所", EXCHANGE_BJ: "北京证券交易所"}

    # 股票代码正则校验
    STOCK_CODE_PATTERN = re.compile(r"^\d{6}(\.[A-Z]{2})?$")

    @classmethod
    def normalize_code(cls, code: str) -> str:
        """标准化股票代码，转换为 代码.交易所 格式
        示例：
            '600000' → '600000.SH'
            '000001.sz' → '000001.SZ'
            '830000' → '830000.BJ'
        """
        if not code:
            raise ValueError("股票代码不能为空")

        code = code.strip().upper()

        if not cls.STOCK_CODE_PATTERN.match(code):
            raise ValueError(f"无效的股票代码格式: {code}")

        # 已经包含交易所后缀
        if "." in code:
            parts = code.split(".")
            if len(parts) != 2:
                raise ValueError(f"无效的股票代码格式: {code}")
            number, exchange = parts
            if exchange in [cls.EXCHANGE_SH, cls.EXCHANGE_SZ, cls.EXCHANGE_BJ]:
                return code
            else:
                # 尝试识别交易所
                exchange = cls.guess_exchange(number)
                return f"{number}.{exchange}"

        # 只有代码，识别交易所
        exchange = cls.guess_exchange(code)
        return f"{code}.{exchange}"

    @classmethod
    def guess_exchange(cls, code: str) -> str:
        """根据股票代码猜测交易所"""
        if len(code) != 6:
            raise ValueError(f"股票代码必须为6位数字: {code}")

        # 上交所：
        # 60开头：主板
        # 688开头：科创板
        # 5开头：基金、权证
        if code.startswith(("60", "688", "5", "11", "13")):
            return cls.EXCHANGE_SH

        # 深交所：
        # 00开头：主板
        # 30开头：创业板
        # 1开头：基金、债券
        elif code.startswith(("00", "30", "1", "12", "15")):
            return cls.EXCHANGE_SZ

        # 北交所：
        # 8开头：精选层、创新层
        # 4开头：基础层
        # 9开头：北交所上市股票（如连城数控 920368）
        elif code.startswith(("8", "4", "9")):
            return cls.EXCHANGE_BJ

        else:
            raise ValueError(f"无法识别交易所的股票代码: {code}")

    @classmethod
    def get_board(cls, code: str) -> str:
        """获取股票所属板块"""
        code = cls.normalize_code(code).split(".")[0]

        if code.startswith("688"):
            return "科创板"
        elif code.startswith("30"):
            return "创业板"
        elif code.startswith("8") or code.startswith("4"):
            return "北交所"
        elif code.startswith("60") or code.startswith("00"):
            return "主板"
        elif code.startswith("5") or code.startswith("1"):
            return "基金/债券"
        else:
            return "其他"

    @classmethod
    def get_price_limit(cls, code: str, is_st: bool = False, is_registration: bool = True) -> float:
        """获取股票涨跌幅限制
        Args:
            code: 股票代码
            is_st: 是否是ST股票
            is_registration: 是否是注册制
        Returns:
            涨跌幅限制比例，如0.1表示10%
        """
        board = cls.get_board(code)

        if is_st:
            return 0.05  # ST股票5%涨跌幅
        elif board in ["科创板", "创业板"]:
            return 0.20 if is_registration else 0.10  # 注册制下20%
        elif board == "北交所":
            return 0.30  # 北交所30%涨跌幅
        else:
            return 0.10  # 主板10%涨跌幅

    @classmethod
    def get_tick_size(cls, code: str) -> float:
        """获取最小报价单位"""
        board = cls.get_board(code)
        if board == "北交所":
            return 0.01  # 北交所股票最小变动单位0.01元
        # A股主板、创业板、科创板都是0.01元
        return 0.01

    @classmethod
    def validate_order_quantity(cls, code: str, quantity: int) -> Tuple[bool, str]:
        """验证下单数量是否合规"""
        board = cls.get_board(code)

        if quantity <= 0:
            return False, "下单数量必须大于0"

        if board in ["科创板", "北交所"]:
            if quantity % 200 != 0 and quantity != 200:
                return False, f"{board}下单数量必须是200股的整数倍"
            if quantity > 100000:
                return False, f"{board}单笔下单最大数量为10万股"
        else:
            if quantity % 100 != 0:
                return False, "下单数量必须是100股的整数倍"
            if quantity > 1000000:
                return False, "单笔下单最大数量为100万股"

        return True, "合规"

    @classmethod
    def split_code(cls, code: str) -> Tuple[str, str]:
        """分割股票代码和交易所"""
        normalized_code = cls.normalize_code(code)
        parts = normalized_code.split(".")
        return parts[0], parts[1]

    @classmethod
    def is_index(cls, code: str) -> bool:
        """判断是否是指数代码"""
        code_num = cls.normalize_code(code).split(".")[0]
        # 上证指数：000001，深证成指：399001，创业板指：399006，科创50：000688等
        return code_num.startswith(("000", "399")) and len(code_num) == 6

    @classmethod
    def is_fund(cls, code: str) -> bool:
        """判断是否是基金代码"""
        code_num = cls.normalize_code(code).split(".")[0]
        return code_num.startswith(("5", "1", "15", "16", "51"))

    @classmethod
    def is_bond(cls, code: str) -> bool:
        """判断是否是债券代码"""
        code_num = cls.normalize_code(code).split(".")[0]
        return code_num.startswith(("11", "12", "13"))

    @classmethod
    def get_stock_type(cls, code: str) -> str:
        """获取证券类型"""
        if cls.is_index(code):
            return "指数"
        elif cls.is_fund(code):
            return "基金"
        elif cls.is_bond(code):
            return "债券"
        else:
            return "股票"

    @classmethod
    def format_for_display(cls, code: str) -> str:
        """格式化股票代码用于显示"""
        try:
            code_num, exchange = cls.split_code(code)
            return f"{code_num}({cls.EXCHANGE_NAMES[exchange]})"
        except:
            return code
