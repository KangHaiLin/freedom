"""
回测报告生成模块
生成文本/JSON/HTML格式回测报告
"""

from .report_generator import generate_html_report, generate_json_report, generate_text_report, save_report

__all__ = [
    "generate_json_report",
    "generate_text_report",
    "generate_html_report",
    "save_report",
]
