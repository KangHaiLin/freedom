"""
数据归一化标准化处理器
支持Min-Max归一化、Z-score标准化、Robust缩放、对数变换、Winsorize截断
支持拟合并缓存缩放参数，用于训练集测试集分开处理
"""

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class NormalizationProcessor(BaseProcessor):
    """数据归一化标准化处理器"""

    def __init__(self, config: Dict = None):
        super().__init__(config=config)
        # 存储拟合好的缩放器
        self.scalers: Dict[str, Any] = {}
        self.fitted = False

    def process(
        self, data: Any, method: str = "minmax", cols: Optional[List[str]] = None, fit: bool = True, **kwargs
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        归一化处理入口
        Args:
            data: 输入数据，DataFrame或numpy数组
            method: 归一化方法，支持: 'minmax', 'zscore', 'robust', 'log', 'winsorize'
            cols: 需要处理的列名列表（DataFrame时使用），None表示所有数值列
            fit: 是否拟合（重新计算参数），False时使用已拟合的参数
            **kwargs: 其他参数
        Returns:
            归一化后的数据
        """
        if not self.validate_input(data):
            logger.warning(f"{self.name}: 输入数据验证失败")
            return data

        if isinstance(data, pd.DataFrame):
            return self._process_dataframe(data, method, cols, fit, **kwargs)
        elif isinstance(data, np.ndarray):
            return self._process_array(data, method, fit, **kwargs)
        else:
            logger.warning(f"{self.name}: 不支持的数据类型: {type(data)}")
            return data

    def _process_dataframe(
        self, df: pd.DataFrame, method: str, cols: Optional[List[str]], fit: bool, **kwargs
    ) -> pd.DataFrame:
        """处理DataFrame"""
        df = df.copy()

        # 如果未指定列，选择所有数值列
        if cols is None:
            cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not cols:
            logger.warning(f"{self.name}: 没有数值列需要归一化")
            return df

        if method == "minmax":
            feature_range = kwargs.get("feature_range", (0, 1))
            df = self._minmax_df(df, cols, feature_range, fit)
        elif method == "zscore":
            df = self._zscore_df(df, cols, fit)
        elif method == "robust":
            df = self._robust_df(df, cols, fit)
        elif method == "log":
            offset = kwargs.get("offset", 1e-8)
            df = self._log_transform_df(df, cols, offset)
        elif method == "winsorize":
            limits = kwargs.get("limits", (0.01, 0.01))
            df = self._winsorize_df(df, cols, limits)
        else:
            logger.warning(f"{self.name}: 未知的归一化方法: {method}")

        return df

    def _process_array(self, arr: np.ndarray, method: str, fit: bool, **kwargs) -> np.ndarray:
        """处理numpy数组"""
        if method == "minmax":
            feature_range = kwargs.get("feature_range", (0, 1))
            return self._minmax_array(arr, feature_range, fit)
        elif method == "zscore":
            return self._zscore_array(arr, fit)
        elif method == "robust":
            return self._robust_array(arr, fit)
        elif method == "log":
            offset = kwargs.get("offset", 1e-8)
            return self._log_transform_array(arr, offset)
        elif method == "winsorize":
            limits = kwargs.get("limits", (0.01, 0.01))
            return self._winsorize_array(arr, limits)
        else:
            logger.warning(f"{self.name}: 未知的归一化方法: {method}")
            return arr

    def _minmax_df(self, df: pd.DataFrame, cols: List[str], feature_range: tuple, fit: bool) -> pd.DataFrame:
        """Min-Max归一化到指定范围（默认0-1）"""
        key = "minmax_" + "_".join(cols)

        if fit:
            scaler = MinMaxScaler(feature_range=feature_range)
            df[cols] = scaler.fit_transform(df[cols])
            self.scalers[key] = scaler
            self.fitted = True
        else:
            if key in self.scalers:
                df[cols] = self.scalers[key].transform(df[cols])
            else:
                logger.warning(f"{self.name}: scaler未拟合，跳过: {key}")

        return df

    def _minmax_array(self, arr: np.ndarray, feature_range: tuple, fit: bool) -> np.ndarray:
        """Min-Max归一化numpy数组"""
        key = "minmax_array"

        if fit:
            scaler = MinMaxScaler(feature_range=feature_range)
            result = scaler.fit_transform(arr)
            self.scalers[key] = scaler
            self.fitted = True
            return result
        else:
            if key in self.scalers:
                return self.scalers[key].transform(arr)
            else:
                logger.warning(f"{self.name}: scaler未拟合，返回原数组")
                return arr

    def _zscore_df(self, df: pd.DataFrame, cols: List[str], fit: bool) -> pd.DataFrame:
        """Z-score标准化，均值0标准差1"""
        key = "zscore_" + "_".join(cols)

        if fit:
            scaler = StandardScaler()
            df[cols] = scaler.fit_transform(df[cols])
            self.scalers[key] = scaler
            self.fitted = True
        else:
            if key in self.scalers:
                df[cols] = self.scalers[key].transform(df[cols])
            else:
                logger.warning(f"{self.name}: scaler未拟合，跳过: {key}")

        return df

    def _zscore_array(self, arr: np.ndarray, fit: bool) -> np.ndarray:
        """Z-score标准化numpy数组"""
        key = "zscore_array"

        if fit:
            scaler = StandardScaler()
            result = scaler.fit_transform(arr)
            self.scalers[key] = scaler
            self.fitted = True
            return result
        else:
            if key in self.scalers:
                return self.scalers[key].transform(arr)
            else:
                logger.warning(f"{self.name}: scaler未拟合，返回原数组")
                return arr

    def _robust_df(self, df: pd.DataFrame, cols: List[str], fit: bool) -> pd.DataFrame:
        """Robust缩放，对异常值更鲁棒，使用中位数和四分位距"""
        key = "robust_" + "_".join(cols)

        if fit:
            scaler = RobustScaler()
            df[cols] = scaler.fit_transform(df[cols])
            self.scalers[key] = scaler
            self.fitted = True
        else:
            if key in self.scalers:
                df[cols] = self.scalers[key].transform(df[cols])
            else:
                logger.warning(f"{self.name}: scaler未拟合，跳过: {key}")

        return df

    def _robust_array(self, arr: np.ndarray, fit: bool) -> np.ndarray:
        """Robust缩放numpy数组"""
        key = "robust_array"

        if fit:
            scaler = RobustScaler()
            result = scaler.fit_transform(arr)
            self.scalers[key] = scaler
            self.fitted = True
            return result
        else:
            if key in self.scalers:
                return self.scalers[key].transform(arr)
            else:
                logger.warning(f"{self.name}: scaler未拟合，返回原数组")
                return arr

    def _log_transform_df(self, df: pd.DataFrame, cols: List[str], offset: float) -> pd.DataFrame:
        """对数变换，压缩偏态数据"""
        df = df.copy()
        for col in cols:
            # 确保数据为正，加上偏移
            df[col] = np.log(df[col] + offset)
        return df

    def _log_transform_array(self, arr: np.ndarray, offset: float) -> np.ndarray:
        """对数变换numpy数组"""
        return np.log(arr + offset)

    def _winsorize_df(self, df: pd.DataFrame, cols: List[str], limits: tuple) -> pd.DataFrame:
        """
        Winsorize截断，将上下百分位的极端值截断
        limits: (lower, upper) 截断百分比
        """
        df = df.copy()
        for col in cols:
            lower = df[col].quantile(limits[0])
            upper = df[col].quantile(1 - limits[1])
            df[col] = df[col].clip(lower=lower, upper=upper)
        return df

    def _winsorize_array(self, arr: np.ndarray, limits: tuple) -> np.ndarray:
        """Winsorize截断numpy数组"""
        lower = np.quantile(arr, limits[0])
        upper = np.quantile(arr, 1 - limits[1])
        return np.clip(arr, lower, upper)

    def inverse_transform(self, data: Any, method: str = "minmax", cols: Optional[List[str]] = None) -> Any:
        """
        逆变换，恢复原始数据范围
        Args:
            data: 归一化后的数据
            method: 归一化方法
            cols: 处理的列
        Returns:
            逆变换后的数据
        """
        key_prefix = method
        if cols:
            key = key_prefix + "_" + "_".join(cols)
        else:
            key = key_prefix + "_array"

        if key not in self.scalers:
            logger.warning(f"{self.name}: 找不到对应的scaler: {key}")
            return data

        if isinstance(data, pd.DataFrame):
            df = data.copy()
            if cols:
                df[cols] = self.scalers[key].inverse_transform(df[cols])
            return df
        else:
            return self.scalers[key].inverse_transform(data)

    def get_scaler(self, key: str) -> Optional[Any]:
        """获取已拟合的缩放器"""
        return self.scalers.get(key)

    def clear_scalers(self):
        """清空所有缩放器"""
        self.scalers.clear()
        self.fitted = False
        logger.info(f"{self.name}: 已清空所有缩放器参数")
