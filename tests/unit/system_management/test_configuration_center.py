"""
测试配置中心
"""

import os
import tempfile

from src.system_management.configuration_center import (
    ConfigManager,
    ConfigProvider,
    ConfigSource,
    EnvConfigSource,
    FileConfigSource,
)


def test_env_config_source():
    """测试环境变量配置源"""
    # 设置测试环境变量
    os.environ["QUANT_TEST_INT"] = "42"
    os.environ["QUANT_TEST_BOOL"] = "true"
    os.environ["QUANT_TEST_FLOAT"] = "3.14"
    os.environ["QUANT_TEST_STRING"] = "hello"

    env_source = EnvConfigSource(prefix="QUANT_")

    # QUANT_TEST_INT -> test.int (下划线转换为点)
    assert env_source.get("test.int") == 42
    assert env_source.get("test.bool") is True
    assert env_source.get("test.float") == 3.14
    assert env_source.get("test.string") == "hello"
    assert env_source.has("test.int")
    assert not env_source.has("not_exists")


def test_file_config_source_yaml():
    """测试 YAML 文件配置源"""
    yaml_content = """
database:
  host: localhost
  port: 5432
  enabled: true
max_connections: 100
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        file_source = FileConfigSource(temp_path)
        assert file_source.get("database.host") == "localhost"
        assert file_source.get("database.port") == 5432
        assert file_source.get("database.enabled") is True
        assert file_source.get("max_connections") == 100
        assert file_source.has("database.host")
        assert not file_source.has("not.exists")
    finally:
        os.unlink(temp_path)


def test_file_config_source_json():
    """测试 JSON 文件配置源"""
    json_content = """
{
  "app": {
    "name": "quant",
    "debug": true,
    "port": 8000
  }
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json_content)
        temp_path = f.name

    try:
        file_source = FileConfigSource(temp_path)
        assert file_source.get("app.name") == "quant"
        assert file_source.get("app.debug") is True
        assert file_source.get("app.port") == 8000
    finally:
        os.unlink(temp_path)


def test_config_provider_multi_source():
    """测试多源配置合并"""
    # 设置环境变量（高优先级）
    os.environ["TEST_APP_PORT"] = "9000"

    provider = ConfigProvider()

    # 添加低优先级源
    class DummySource(ConfigSource):
        def __init__(self):
            self.data = {
                "app.name": "test",
                "app.port": 8000,
                "app.debug": True,
            }

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value):
            return False

        def has(self, key):
            return key in self.data

        def load(self):
            return self.data

    provider.add_source(DummySource(), priority=0)
    provider.add_source(EnvConfigSource(prefix="TEST_"), priority=100)

    # 低优先级
    assert provider.get("app.name") == "test"
    assert provider.get("app.debug") is True
    # 环境变量覆盖
    assert provider.get("app.port") == 9000
    # 默认值
    assert provider.get("not.exists", "default") == "default"


def test_config_provider_type_conversion():
    """测试类型转换"""
    provider = ConfigProvider()

    class DummySource(ConfigSource):
        def get(self, key):
            return "42" if key == "int_val" else "true" if key == "bool_val" else "3.14"

        def set(self, key, value):
            return False

        def has(self, key):
            return True

        def load(self):
            return {}

    provider.add_source(DummySource())

    assert provider.get("int_val", expected_type=int) == 42
    assert provider.get("bool_val", expected_type=bool) is True
    assert provider.get("int_val", expected_type=float) == 42.0


def test_config_manager():
    """测试配置管理器"""
    manager = ConfigManager()
    # 重新初始化单例
    manager._provider = ConfigProvider()
    manager._initialized = True

    manager.initialize(None, env_prefix="TEST_")

    os.environ["TEST_CONFIG"] = "test_value"
    manager.reload()

    assert manager.get("config") == "test_value"
    assert manager.has("config")
    assert not manager.has("not_exists")

    # 测试类型转换
    os.environ["TEST_PORT"] = "8080"
    manager.reload()
    assert manager.get("port", expected_type=int) == 8080


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
