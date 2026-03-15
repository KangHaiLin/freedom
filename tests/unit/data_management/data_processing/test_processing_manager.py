"""
Unit tests for processing_manager.py
"""
import pytest
import pandas as pd
import numpy as np
from src.data_management.data_processing.processing_manager import ProcessingManager, processing_manager
from src.data_management.data_processing.base_processor import BaseProcessor


def test_manager_init():
    """测试管理器初始化"""
    manager = ProcessingManager()

    # 所有处理器都应该加载了
    assert 'transformation' in manager.processors
    assert 'aggregation' in manager.processors
    assert 'indicators' in manager.processors
    assert 'normalization' in manager.processors
    assert 'merging' in manager.processors
    assert 'batch' in manager.processors
    assert 'stream' in manager.processors
    assert len(manager.processors) == 7


def test_get_processor():
    """测试获取处理器"""
    manager = ProcessingManager()

    transformation = manager.get_processor('transformation')
    assert transformation is not None
    assert isinstance(transformation, BaseProcessor)


def test_add_remove_processor():
    """测试添加移除处理器"""
    manager = ProcessingManager()
    initial_count = len(manager.processors)

    # 添加自定义处理器
    class TestProcessor(BaseProcessor):
        def process(self, data, **kwargs):
            return data

    manager.add_processor('test', TestProcessor())

    assert len(manager.processors) == initial_count + 1
    assert 'test' in manager.processors

    # 移除
    manager.remove_processor('test')
    assert len(manager.processors) == initial_count
    assert 'test' not in manager.processors


def test_process_specific_processor():
    """测试处理调用特定处理器"""
    manager = ProcessingManager()

    # 测试转换处理器
    data = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
    result = manager.process('transformation', data, transform_type='list_to_df')

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_process_pipeline():
    """测试处理流水线"""
    manager = ProcessingManager()

    df = pd.DataFrame({
        'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'volume': [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000]
    })

    pipeline = [
        {
            'processor': 'transformation',
            'params': {}
        },
        {
            'processor': 'indicators',
            'params': {'indicators': ['sma', 'rsi']}
        }
    ]

    result = manager.process_pipeline(df, pipeline)

    assert isinstance(result, pd.DataFrame)
    assert any(col.startswith('sma_') for col in result.columns)
    assert any(col.startswith('rsi_') for col in result.columns)


def test_convenience_methods():
    """测试便捷方法"""
    manager = ProcessingManager()

    # 测试transform
    data = [{'a': 1}, {'a': 2}]
    result = manager.transform(data, transform_type='list_to_df')
    assert isinstance(result, pd.DataFrame)

    # 测试calculate_indicators
    df = pd.DataFrame({
        'open': [10, 11, 12],
        'high': [11, 12, 13],
        'low': [9, 10, 11],
        'close': [10, 11, 12],
        'volume': [1000, 1000, 1000]
    })
    result = manager.calculate_indicators(df, indicators=['sma'])
    assert 'sma_5' in result.columns or 'sma_10' in result.columns


def test_health_check():
    """测试健康检查"""
    manager = ProcessingManager()
    health = manager.health_check()

    assert 'status' in health
    assert 'processor_count' in health
    assert 'processors' in health
    assert 'check_time' in health
    assert health['status'] == 'healthy'
    assert health['processor_count'] == 7


def test_get_processor_info():
    """测试获取所有处理器信息"""
    manager = ProcessingManager()
    info = manager.get_processor_info()

    assert isinstance(info, list)
    assert len(info) == 7
    for item in info:
        assert 'name' in item
        assert 'enabled' in item


def test_global_instance_exists():
    """测试全局实例存在"""
    assert processing_manager is not None
    assert isinstance(processing_manager, ProcessingManager)
    assert len(processing_manager.processors) > 0


def test_global_health_check():
    """测试全局实例健康检查"""
    health = processing_manager.health_check()
    assert health['status'] == 'healthy'
