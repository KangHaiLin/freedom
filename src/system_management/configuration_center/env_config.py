"""
配置中心 - 环境变量配置源
从系统环境变量读取配置，支持类型转换和前缀过滤
"""

import os
from typing import Any, Dict, Optional

from .base_config import ConfigSource


class EnvConfigSource(ConfigSource):
    """环境变量配置源"""

    def __init__(
        self,
        prefix: str = "",
        lowercase: bool = True,
        separator: str = "_",
    ):
        """
        初始化环境变量配置源

        Args:
            prefix: 环境变量前缀，例如 'QUANT_' 会只加载以此开头的变量
            lowercase: 是否转换为小写键名
            separator: 分隔符，用于将下划线转换为点分隔
        """
        self.prefix = prefix
        self.lowercase = lowercase
        self.separator = separator
        self._cache: Dict[str, Any] = {}
        self._load_all()

    def _load_all(self) -> None:
        """加载所有匹配前缀的环境变量"""
        self._cache.clear()
        for env_key, env_value in os.environ.items():
            if self.prefix and not env_key.startswith(self.prefix):
                continue

            # 移除前缀
            if self.prefix:
                key = env_key[len(self.prefix) :]
            else:
                key = env_key

            # 转换为小写
            if self.lowercase:
                key = key.lower()

            # 将下划线替换为点，形成层级键名
            if self.separator:
                key = key.replace(self.separator, ".")

            # 尝试类型转换
            self._cache[key] = self._convert_type(env_value)

    def _convert_type(self, value: str) -> Any:
        """
        将字符串值转换为合适的类型

        支持：int, float, bool, str
        """
        # 空字符串
        if value == "":
            return ""

        # 布尔值判断
        lower_value = value.lower()
        if lower_value in ("true", "yes", "1", "on"):
            return True
        if lower_value in ("false", "no", "0", "off"):
            return False

        # 尝试整数
        try:
            int_val = int(value)
            return int_val
        except ValueError:
            pass

        # 尝试浮点数
        try:
            float_val = float(value)
            return float_val
        except ValueError:
            pass

        # 保持字符串
        return value

    def get(self, key: str) -> Optional[Any]:
        """获取配置值"""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> bool:
        """设置配置值（环境变量不支持运行时设置）"""
        # 环境变量通常不支持运行时修改，这里只更新缓存
        self._cache[key] = value
        return True

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return key in self._cache

    def load(self) -> Dict[str, Any]:
        """加载所有配置"""
        self._load_all()
        return self._cache.copy()
