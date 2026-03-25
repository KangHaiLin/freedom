"""
Unit tests for transformation_processor.py
"""

import pandas as pd

from src.data_management.data_processing.transformation_processor import TransformationProcessor


def test_list_to_dataframe():
    """测试列表转DataFrame"""
    processor = TransformationProcessor()
    data = [
        {"ts_code": "000001.SZ", "close": 10.5, "volume": 10000},
        {"ts_code": "000002.SZ", "close": 20.3, "volume": 20000},
    ]

    df = processor.list_to_dataframe(data)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["ts_code", "close", "volume"]


def test_dataframe_to_list():
    """测试DataFrame转列表"""
    processor = TransformationProcessor()
    df = pd.DataFrame({"ts_code": ["000001.SZ", "000002.SZ"], "close": [10.5, 20.3], "volume": [10000, 20000]})

    result = processor.dataframe_to_list(df)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["ts_code"] == "000001.SZ"
    assert result[0]["close"] == 10.5


def test_convert_dtypes():
    """测试数据类型转换"""
    processor = TransformationProcessor()
    df = pd.DataFrame({"close": ["10.5", "20.3"], "volume": ["10000", "20000"], "date": ["2024-01-01", "2024-01-02"]})

    dtype_map = {"close": "float", "volume": "int"}
    result = processor.convert_dtypes(df, dtype_map)

    assert result["close"].dtype == float
    assert result["volume"].dtype == "Int64" or pd.api.types.is_integer_dtype(result["volume"])


def test_rename_columns():
    """测试列重命名"""
    processor = TransformationProcessor()
    df = pd.DataFrame({"c": [1, 2, 3], "v": [100, 200, 300]})

    rename_map = {"c": "close", "v": "volume"}
    result = processor.rename_columns(df, rename_map)

    assert "close" in result.columns
    assert "volume" in result.columns
    assert "c" not in result.columns


def test_normalize_datetime():
    """测试日期时间标准化"""
    processor = TransformationProcessor()
    df = pd.DataFrame(
        {"trade_date": [20240101, 20240102], "trade_time": ["2024-01-01 09:30:00", "2024-01-01 09:31:00"]}
    )

    result = processor.normalize_datetime(df, datetime_cols=["trade_time"], date_cols=["trade_date"])
    assert result is not None
    assert len(result) == 2


def test_resample_tick_to_minute():
    """测试Tick重采样到分钟线"""
    processor = TransformationProcessor()
    # 创建模拟Tick数据
    times = pd.date_range("2024-01-01 09:30:00", "2024-01-01 09:34:59", freq="1min")
    df = pd.DataFrame(
        {
            "trade_time": times,
            "open": [10.0, 10.1, 10.2, 10.3, 10.4],
            "high": [10.2, 10.3, 10.4, 10.5, 10.6],
            "low": [9.9, 10.0, 10.1, 10.2, 10.3],
            "close": [10.1, 10.2, 10.3, 10.4, 10.5],
            "volume": [100, 200, 300, 400, 500],
            "amount": [1000, 2000, 3000, 4000, 5000],
        }
    )

    # 重采样到2分钟
    result = processor.resample(df, rule="2T", datetime_col="trade_time")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3  # 0-1, 2-3, 4 -> 3个区间
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "close" in result.columns
    assert "volume" in result.columns


def test_process_dispatch():
    """测试process分发"""
    processor = TransformationProcessor()
    data = [{"a": 1}, {"a": 2}]

    # 测试不同类型分发
    result = processor.process(data, transform_type="list_to_df")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
