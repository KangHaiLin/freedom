"""
数据处理管理器
统一管理所有数据处理器，提供统一处理接口，支持流水线执行
"""
from typing import Any, Dict, List, Optional, Any
import logging

from .base_processor import BaseProcessor
from .processor_result import ProcessingResult
from .transformation_processor import TransformationProcessor
from .aggregation_processor import AggregationProcessor
from .indicator_calculator import IndicatorCalculator
from .normalization_processor import NormalizationProcessor
from .merging_processor import MergingProcessor
from .batch_processor import BatchProcessor
from .stream_processor import StreamProcessor

from common.config import settings
from common.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class ProcessingManager:
    """数据处理管理器，统一管理所有处理器"""

    def __init__(self):
        self.config = settings.PROCESSING_CONFIG
        self.processors: Dict[str, BaseProcessor] = {}
        self._init_processors()

    def _init_processors(self):
        """初始化所有处理器实例"""
        try:
            # 数据转换
            if self.config.get('enable_transformation', True):
                self.processors['transformation'] = TransformationProcessor(
                    self.config.get('transformation', {})
                )
                logger.info("数据转换处理器已加载")

            # 数据聚合
            if self.config.get('enable_aggregation', True):
                self.processors['aggregation'] = AggregationProcessor(
                    self.config.get('aggregation', {})
                )
                logger.info("数据聚合处理器已加载")

            # 指标计算
            if self.config.get('enable_indicators', True):
                self.processors['indicators'] = IndicatorCalculator(
                    self.config.get('indicators', {})
                )
                logger.info("指标计算器已加载")

            # 归一化标准化
            if self.config.get('enable_normalization', True):
                self.processors['normalization'] = NormalizationProcessor(
                    self.config.get('normalization', {})
                )
                logger.info("归一化处理器已加载")

            # 数据合并
            if self.config.get('enable_merging', True):
                self.processors['merging'] = MergingProcessor(
                    self.config.get('merging', {})
                )
                logger.info("数据合并处理器已加载")

            # 批处理
            if self.config.get('enable_batch', True):
                self.processors['batch'] = BatchProcessor(
                    self.config.get('batch', {})
                )
                logger.info("批处理器已加载")

            # 流处理
            if self.config.get('enable_stream', True):
                self.processors['stream'] = StreamProcessor(
                    self.config.get('stream', {})
                )
                logger.info("流处理器已加载")

            logger.info(f"数据处理管理器初始化完成，共加载{len(self.processors)}个处理器")

        except Exception as e:
            logger.error(f"初始化数据处理管理器失败: {e}")
            raise

    def add_processor(self, name: str, processor: BaseProcessor):
        """添加自定义处理器"""
        self.processors[name] = processor
        logger.info(f"添加自定义处理器: {name}")

    def get_processor(self, name: str) -> Optional[BaseProcessor]:
        """获取处理器实例"""
        return self.processors.get(name)

    def remove_processor(self, name: str):
        """移除处理器"""
        if name in self.processors:
            del self.processors[name]
            logger.info(f"移除处理器: {name}")

    def process(self, processor_name: str, data: Any, **kwargs) -> Any:
        """
        使用指定处理器处理数据
        Args:
            processor_name: 处理器名称
            data: 输入数据
            **kwargs: 处理参数
        Returns:
            处理结果
        """
        processor = self.get_processor(processor_name)
        if not processor:
            logger.error(f"处理器不存在: {processor_name}")
            return None

        if not processor.enabled:
            logger.warning(f"处理器已禁用: {processor_name}")
            return data

        return processor.process(data, **kwargs)

    def process_pipeline(self, data: Any, pipeline: List[Dict]) -> Any:
        """
        执行处理流水线，依次执行多个处理器
        Args:
            data: 输入数据
            pipeline: 流水线配置，每个元素是 {'processor': 名称, 'params': 参数}
        Returns:
            最终处理结果
        """
        current_data = data
        for step in pipeline:
            processor_name = step.get('processor')
            params = step.get('params', {})

            processor = self.get_processor(processor_name)
            if not processor or not processor.enabled:
                logger.warning(f"跳过处理器: {processor_name}")
                continue

            try:
                current_data = processor.process(current_data, **params)
            except Exception as e:
                logger.error(f"流水线步骤{processor_name}执行失败: {e}")
                raise

        return current_data

    # 便捷方法
    def transform(self, data: Any, **kwargs) -> Any:
        """数据转换便捷方法"""
        return self.process('transformation', data, **kwargs)

    def aggregate(self, data: Any, **kwargs) -> Any:
        """数据聚合便捷方法"""
        return self.process('aggregation', data, **kwargs)

    def calculate_indicators(self, data: Any, **kwargs) -> Any:
        """计算指标便捷方法"""
        return self.process('indicators', data, **kwargs)

    def normalize(self, data: Any, **kwargs) -> Any:
        """归一化便捷方法"""
        return self.process('normalization', data, **kwargs)

    def merge(self, data: Any, **kwargs) -> Any:
        """数据合并便捷方法"""
        return self.process('merging', data, **kwargs)

    def batch_process(self, data: Any, **kwargs) -> ProcessingResult:
        """批处理便捷方法"""
        return self.process('batch', data, **kwargs)

    def stream_process(self, data: Any, **kwargs) -> Any:
        """流处理便捷方法"""
        return self.process('stream', data, **kwargs)

    def health_check(self) -> Dict:
        """健康检查"""
        processor_health = {}
        for name, processor in self.processors.items():
            processor_health[name] = processor.health_check()

        return {
            'status': 'healthy',
            'processor_count': len(self.processors),
            'processors': processor_health,
            'check_time': DateTimeUtils.now_str()
        }

    def get_processor_info(self) -> List[Dict]:
        """获取所有处理器信息"""
        return [processor.get_processor_info() for processor in self.processors.values()]


# 全局数据处理管理器实例
processing_manager = ProcessingManager()
