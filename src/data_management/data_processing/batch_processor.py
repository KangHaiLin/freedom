"""
批处理器
负责大数据集分块处理、按股票分组并行处理、处理流水线、从存储读写数据
"""

import concurrent.futures
import logging
from typing import Any, Callable, Dict, List

import pandas as pd

from ..data_storage.storage_manager import storage_manager
from .base_processor import BaseProcessor
from .processor_result import ProcessingResult

logger = logging.getLogger(__name__)


class BatchProcessor(BaseProcessor):
    """批数据处理器"""

    def __init__(
        self, config: Dict = None, chunk_size: int = None, max_workers: int = None, enable_parallel: bool = None
    ):
        super().__init__(config=config)
        self.chunk_size = chunk_size if chunk_size is not None else self.config.get("chunk_size", 10000)
        self.max_workers = max_workers if max_workers is not None else self.config.get("max_workers", 4)
        self.enable_parallel = (
            enable_parallel if enable_parallel is not None else self.config.get("enable_parallel", True)
        )

    def process(self, data: Any, processors: List[Callable], **kwargs) -> ProcessingResult:
        """
        执行批处理流水线，依次应用多个处理器
        Args:
            data: 输入数据，可以是DataFrame、或者存储查询条件
            processors: 处理器函数列表，按顺序执行
        Returns:
            处理结果
        """
        import time

        start_time = time.time()

        try:
            # 如果data是字典，认为是查询条件，从存储读取
            if isinstance(data, dict) and "table_name" in data:
                data = self._read_from_storage(data)

            if not self.validate_input(data):
                self._record_processing(start_time)
                return ProcessingResult.failure(
                    processor_name=self.name, message="输入数据验证失败", processing_time=time.time() - start_time
                )

            # 分块处理
            if isinstance(data, pd.DataFrame) and len(data) > self.chunk_size:
                result = self.process_in_chunks(data, processors, **kwargs)
            else:
                # 整块处理
                result = self.process_pipeline(data, processors, **kwargs)

            processing_time = time.time() - start_time
            self._record_processing(start_time)

            metrics = {
                "input_rows": len(data) if isinstance(data, pd.DataFrame) else 0,
                "output_rows": len(result) if isinstance(result, pd.DataFrame) else 0,
                "processing_time": processing_time,
            }

            return ProcessingResult.success(
                processor_name=self.name, data=result, metrics=metrics, processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"{self.name}: 批处理异常: {e}")
            self._record_processing(start_time)
            return ProcessingResult.failure(
                processor_name=self.name, message=f"批处理异常: {str(e)}", processing_time=processing_time
            )

    def process_in_chunks(self, df: pd.DataFrame, processors: List[Callable], **kwargs) -> pd.DataFrame:
        """
        分块处理大数据集
        Args:
            df: 输入DataFrame
            processors: 处理器函数列表
        Returns:
            处理后的完整DataFrame
        """
        chunks = self._split_dataframe(df, self.chunk_size)
        results = []

        if self.enable_parallel and len(chunks) > 1:
            # 并行处理各个分块
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self.process_pipeline, chunk, processors, **kwargs): i
                    for i, chunk in enumerate(chunks)
                }
                for future in concurrent.futures.as_completed(future_to_chunk):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"{self.name}: 分块处理失败: {e}")
        else:
            # 顺序处理
            for chunk in chunks:
                result = self.process_pipeline(chunk, processors, **kwargs)
                results.append(result)

        # 拼接结果
        if all(isinstance(r, pd.DataFrame) for r in results):
            return pd.concat(results, ignore_index=True)
        elif all(isinstance(r, list) for r in results):
            return [item for sublist in results for item in sublist]
        else:
            return results

    def process_by_stock(
        self, df: pd.DataFrame, processor: Callable[[pd.DataFrame], pd.DataFrame], code_col: str = "ts_code", **kwargs
    ) -> pd.DataFrame:
        """
        按股票分组处理，每组独立应用处理函数
        Args:
            df: 输入DataFrame
            processor: 处理函数，接收单只股票DataFrame返回处理后
            code_col: 股票代码列名
        Returns:
            处理后的完整DataFrame
        """
        groups = [group for _, group in df.groupby(code_col)]
        results = []

        if self.enable_parallel and len(groups) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_group = {executor.submit(processor, group): group for group in groups}
                for future in concurrent.futures.as_completed(future_to_group):
                    try:
                        result = future.result()
                        if isinstance(result, pd.DataFrame) and not result.empty:
                            results.append(result)
                    except Exception as e:
                        logger.error(f"{self.name}: 分组处理失败: {e}")
        else:
            for group in groups:
                try:
                    result = processor(group)
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        results.append(result)
                except Exception as e:
                    logger.error(f"{self.name}: 分组处理失败: {e}")

        return pd.concat(results, ignore_index=True)

    def process_pipeline(self, data: Any, processors: List[Callable], **kwargs) -> Any:
        """
        依次执行处理流水线
        Args:
            data: 输入数据
            processors: 处理器函数列表
        Returns:
            最终处理结果
        """
        current_data = data
        for i, processor in enumerate(processors):
            try:
                if callable(processor):
                    current_data = processor(current_data, **kwargs)
                else:
                    logger.warning(f"{self.name}: 第{i+1}个处理器不可调用")
            except Exception as e:
                logger.error(f"{self.name}: 第{i+1}个处理器执行失败: {e}")
                raise

        return current_data

    def process_and_write(
        self, query_config: Dict, table_name: str, processors: List[Callable], **kwargs
    ) -> ProcessingResult:
        """
        从存储读取数据，处理后回写存储
        Args:
            query_config: 查询配置，包含table_name等
            table_name: 输出表名
            processors: 处理流水线
        Returns:
            处理结果
        """
        import time

        start_time = time.time()

        try:
            # 读取数据
            df = self._read_from_storage(query_config)

            if df.empty:
                return ProcessingResult.success(
                    processor_name=self.name,
                    data=None,
                    metrics={"rows_read": 0, "rows_written": 0},
                    processing_time=time.time() - start_time,
                )

            # 处理
            result = self.process_pipeline(df, processors, **kwargs)

            # 回写
            if isinstance(result, pd.DataFrame) and not result.empty:
                storage = storage_manager.get_default_storage()
                if storage:
                    storage.write(table_name, result.to_dict("records"))
                    rows_written = len(result)
                else:
                    rows_written = 0
                    logger.warning(f"{self.name}: 无法获取默认存储，未写入")
            else:
                rows_written = 0

            processing_time = time.time() - start_time
            metrics = {"rows_read": len(df), "rows_written": rows_written, "processing_time": processing_time}

            return ProcessingResult.success(
                processor_name=self.name, data=result, metrics=metrics, processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"{self.name}: 处理写入失败: {e}")
            return ProcessingResult.failure(
                processor_name=self.name, message=f"处理写入失败: {str(e)}", processing_time=processing_time
            )

    def _split_dataframe(self, df: pd.DataFrame, chunk_size: int) -> List[pd.DataFrame]:
        """将DataFrame分块"""
        return [df[i : i + chunk_size] for i in range(0, len(df), chunk_size)]

    def _read_from_storage(self, config: Dict) -> pd.DataFrame:
        """从存储读取数据"""
        table_name = config.get("table_name")
        conditions = config.get("conditions", [])
        params = config.get("params", [])
        limit = config.get("limit")

        storage = storage_manager.get_default_storage()
        if not storage:
            logger.warning(f"{self.name}: 无法获取默认存储")
            return pd.DataFrame()

        if hasattr(storage, "query"):
            df = storage.query(table_name, conditions=conditions, params=params, limit=limit)
        elif hasattr(storage, "execute_sql"):
            # 构建简单SQL
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"SELECT * FROM {table_name} WHERE {where_clause}"
            if limit:
                sql += f" LIMIT {limit}"
            df = storage.execute_sql(sql, params=params)
        else:
            logger.warning(f"{self.name}: 存储不支持查询")
            df = pd.DataFrame()

        return df
