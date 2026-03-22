"""
Unit tests for base_processor.py
"""

import numpy as np
import pandas as pd

from src.data_management.data_processing.base_processor import BaseProcessor


class TestProcessor(BaseProcessor):
    """测试用具体处理器"""

    def process(self, data, **kwargs):
        return data


def test_base_processor_init():
    """测试基类初始化"""
    processor = TestProcessor()
    assert processor.name == "TestProcessor"
    assert processor.enabled is True
    assert processor.process_count == 0
    assert processor.enabled is True


def test_base_processor_custom_name():
    """测试自定义名称"""
    processor = TestProcessor(name="CustomProcessor")
    assert processor.name == "CustomProcessor"


def test_validate_input_valid_data():
    """测试输入验证-有效数据"""
    processor = TestProcessor()

    # 非空DataFrame
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert processor.validate_input(df) is True

    # 非空数组
    arr = np.array([1, 2, 3])
    assert processor.validate_input(arr) is True

    # 非None
    data = {"a": 1}
    assert processor.validate_input(data) is True


def test_validate_input_invalid_data():
    """测试输入验证-无效数据"""
    processor = TestProcessor()

    # None
    assert processor.validate_input(None) is False

    # 空DataFrame
    df = pd.DataFrame()
    assert processor.validate_input(df) is False

    # 空数组
    arr = np.array([])
    assert processor.validate_input(arr) is False


def test_get_processor_info():
    """测试获取处理器信息"""
    processor = TestProcessor(config={"param": 1})
    info = processor.get_processor_info()

    assert "name" in info
    assert "type" in info
    assert "enabled" in info
    assert "process_count" in info
    assert "config" in info
    assert info["config"]["param"] == 1


def test_enable_disable():
    """测试启用禁用"""
    processor = TestProcessor()
    assert processor.enabled is True

    processor.disable()
    assert processor.enabled is False

    processor.enable()
    assert processor.enabled is True


def test_health_check():
    """测试健康检查"""
    processor = TestProcessor()
    health = processor.health_check()

    assert "name" in health
    assert "status" in health
    assert "check_time" in health
    assert health["status"] == "healthy"
