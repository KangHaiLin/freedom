"""
策略验证模块
- 过拟合检测
- 参数敏感性分析
- 样本外测试
"""

from .out_of_sample import rolling_window_test, split_sample_test
from .overfit_detector import (
    calculate_drawdown_calmar,
    calculate_information_ratio,
    detect_overfit,
    walk_forward_analysis,
)
from .param_sensitivity import grid_search, scan_parameter, sensitivity_summary

__all__ = [
    "detect_overfit",
    "walk_forward_analysis",
    "calculate_information_ratio",
    "calculate_drawdown_calmar",
    "scan_parameter",
    "grid_search",
    "sensitivity_summary",
    "rolling_window_test",
    "split_sample_test",
]
