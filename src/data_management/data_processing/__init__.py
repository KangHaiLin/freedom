"""
数据处理模块
负责数据转换、衍生指标计算、数据聚合统计、归一化标准化、多源数据合并、批处理和流处理
是数据采集到存储之间的关键环节，闭合完整的数据处理pipeline
"""
from .base_processor import BaseProcessor
from .processor_result import ProcessingResult
from .transformation_processor import TransformationProcessor
from .aggregation_processor import AggregationProcessor
from .indicator_calculator import IndicatorCalculator
from .normalization_processor import NormalizationProcessor
from .merging_processor import MergingProcessor
from .batch_processor import BatchProcessor
from .stream_processor import StreamProcessor
from .processing_manager import ProcessingManager, processing_manager

__all__ = [
    'BaseProcessor',
    'ProcessingResult',
    'TransformationProcessor',
    'AggregationProcessor',
    'IndicatorCalculator',
    'NormalizationProcessor',
    'MergingProcessor',
    'BatchProcessor',
    'StreamProcessor',
    'ProcessingManager',
    'processing_manager'
]
