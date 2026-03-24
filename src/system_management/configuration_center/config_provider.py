"""
配置中心 - 配置提供者
多源配置合并，类型转换，默认值支持，配置验证
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from .base_config import ConfigSource

T = TypeVar("T")


class ConfigProvider:
    """
    配置提供者
    管理多个配置源，支持优先级合并，类型转换，默认值
    优先级：环境变量 > 文件配置 > 默认值
    """

    def __init__(self):
        """初始化配置提供者"""
        self._sources: list[ConfigSource] = []
        self._validators: dict[str, list[Callable[[Any], bool]]] = {}

    def add_source(self, source: ConfigSource, priority: int = 0) -> "ConfigProvider":
        """
        添加配置源

        Args:
            source: 配置源
            priority: 优先级，优先级越高越先被查询，越大越优先
        """
        # 按优先级插入，保持降序
        inserted = False
        for i, s in enumerate(self._sources):
            if priority > self._get_source_priority(s):
                self._sources.insert(i, source)
                inserted = True
                break
        if not inserted:
            self._sources.append(source)
        return self

    def _get_source_priority(self, source: ConfigSource) -> int:
        """获取已添加源的优先级（默认返回 0）"""
        # 我们通过位置推断，这里简化处理
        return 100 - len(self._sources)

    def get(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> Optional[T]:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值
            expected_type: 期望类型，会自动转换

        Returns:
            配置值，如果不存在返回默认值
        """
        # 按优先级从各个源查询
        for source in self._sources:
            if source.has(key):
                value = source.get(key)
                if value is not None:
                    if expected_type is not None:
                        value = self._convert_type(value, expected_type)
                    return value

        # 所有源都没有，返回默认值
        if expected_type is not None and default is not None:
            return self._convert_type(default, expected_type)
        return default

    def get_required(self, key: str, expected_type: Optional[Type[T]] = None) -> T:
        """
        获取必须的配置值，如果不存在抛出异常

        Args:
            key: 配置键
            expected_type: 期望类型

        Raises:
            KeyError: 如果配置不存在

        Returns:
            配置值
        """
        value = self.get(key, None, expected_type)
        if value is None:
            raise KeyError(f"Required configuration key '{key}' not found")
        return value

    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值，会尝试写入第一个支持写入的源

        Args:
            key: 配置键
            value: 配置值

        Returns:
            是否设置成功
        """
        for source in self._sources:
            if source.set(key, value):
                # 验证
                if not self._validate(key, value):
                    return False
                return True
        return False

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        for source in self._sources:
            if source.has(key):
                return True
        return False

    def add_validator(self, key: str, validator: Callable[[Any], bool]) -> None:
        """
        添加配置验证器

        Args:
            key: 配置键
            validator: 验证函数，返回 True 表示验证通过
        """
        if key not in self._validators:
            self._validators[key] = []
        self._validators[key].append(validator)

    def _validate(self, key: str, value: Any) -> bool:
        """验证配置值"""
        if key not in self._validators:
            return True
        for validator in self._validators[key]:
            if not validator(value):
                return False
        return True

    def _convert_type(self, value: Any, expected_type: Type[T]) -> T:
        """
        类型转换

        支持基本类型转换
        """
        # 如果已经是正确类型，直接返回
        if isinstance(value, expected_type):
            return value

        # None 处理
        if value is None:
            return None

        # 泛型处理 - Union 包含 None
        if hasattr(expected_type, "__origin__") and expected_type.__origin__ is Union:
            for t in expected_type.__args__:
                if t is type(None):
                    continue
                try:
                    return self._convert_type(value, t)
                except (ValueError, TypeError):
                    continue
            return None

        # 布尔转换
        if expected_type is bool:
            if isinstance(value, str):
                return expected_type(value.lower() in ("true", "yes", "1", "on"))
            return expected_type(bool(value))

        # 基本类型转换
        try:
            return expected_type(value)
        except (ValueError, TypeError):
            # 如果转换失败，返回默认值形式
            if value == "":
                return expected_type()
            raise

    def reload_all(self) -> Dict[str, Any]:
        """重新加载所有配置源"""
        result = {}
        for source in self._sources:
            result.update(source.load())
        return result

    def get_all(self) -> Dict[str, Any]:
        """获取所有合并后的配置"""
        result = {}
        # 逆序遍历，让高优先级覆盖低优先级
        for source in reversed(self._sources):
            result.update(source.load())
        return result
