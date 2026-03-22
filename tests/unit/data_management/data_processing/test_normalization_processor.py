"""
Unit tests for normalization_processor.py
"""

import numpy as np
import pandas as pd
import pytest

from src.data_management.data_processing.normalization_processor import NormalizationProcessor


def test_minmax_normalization():
    """测试Min-Max归一化"""
    processor = NormalizationProcessor()
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})

    result = processor.process(df, method="minmax", cols=["a", "b"], fit=True)

    # 结果应该在0-1范围内
    assert result["a"].min() == pytest.approx(0)
    assert result["a"].max() == pytest.approx(1)
    assert result["b"].min() == pytest.approx(0)
    assert result["b"].max() == pytest.approx(1)


def test_zscore_normalization():
    """测试Z-score标准化"""
    processor = NormalizationProcessor()
    np.random.seed(42)
    data = np.random.normal(10, 2, 1000)
    df = pd.DataFrame({"value": data})

    result = processor.process(df, method="zscore", cols=["value"], fit=True)

    # 均值接近0，标准差接近1
    assert abs(result["value"].mean()) < 0.1
    assert abs(result["value"].std() - 1) < 0.1


def test_log_transformation():
    """测试对数变换"""
    processor = NormalizationProcessor()
    df = pd.DataFrame({"value": [1, 10, 100, 1000]})

    result = processor.process(df, method="log", cols=["value"], offset=1e-8)

    # log(1000) ≈ 6.9
    assert abs(result["value"].iloc[3] - np.log(1000)) < 0.001


def test_winsorize():
    """测试Winsorize截断"""
    processor = NormalizationProcessor()
    # 创建包含异常值的数据
    df = pd.DataFrame({"value": list(range(100)) + [1000, -1000]})

    result = processor.process(df, method="winsorize", cols=["value"], limits=(0.01, 0.01))

    # 极端值应该被截断
    assert result["value"].max() < 1000
    assert result["value"].min() > -1000


def test_inverse_transform():
    """测试逆变换"""
    processor = NormalizationProcessor()
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})

    # 归一化
    normalized = processor.process(df, method="minmax", cols=["a"], fit=True)
    # 逆变换
    restored = processor.inverse_transform(normalized, method="minmax", cols=["a"])

    # 应该恢复到原始值
    assert np.allclose(df["a"], restored["a"])


def test_robust_scaler():
    """测试Robust缩放"""
    processor = NormalizationProcessor()
    # 数据包含异常值，Robust应该更鲁棒
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 1000]})  # 1000是异常值

    result = processor.process(df, method="robust", cols=["a"], fit=True)
    assert not pd.isna(result["a"]).any()


def test_clear_scalers():
    """测试清空缩放器"""
    processor = NormalizationProcessor()
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    processor.process(df, method="minmax", cols=["a"], fit=True)

    assert processor.fitted is True
    processor.clear_scalers()
    assert processor.fitted is False
    assert len(processor.scalers) == 0


def test_numpy_array_input():
    """测试numpy数组输入"""
    processor = NormalizationProcessor()
    arr = np.array([[1, 2, 3, 4, 5], [10, 20, 30, 40, 50]]).T

    result = processor.process(arr, method="minmax", fit=True)
    assert result.shape == arr.shape
    assert result.min() == pytest.approx(0)
    assert result.max() == pytest.approx(1)
