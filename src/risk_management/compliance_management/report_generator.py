"""
合规报表生成器
生成监管要求的各类合规报送报表
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import pdfkit

    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

logger = __import__("logging").getLogger(__name__)


class ComplianceReportGenerator:
    """
    合规报表生成器
    支持生成日报、月报、异常交易报告等，输出PDF格式
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        初始化报表生成器

        Args:
            template_dir: 模板目录，None使用默认
        """
        if template_dir is None:
            template_dir = str(Path(__file__).parent / "templates")
        self._template_dir = template_dir

        if JINJA2_AVAILABLE:
            self._jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=True,
            )
        else:
            self._jinja_env = None
            logger.warning("jinja2 not available, HTML template rendering disabled")

        self._report_output_dir = Path("reports/compliance")
        self._report_output_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(
        self,
        report_date: Optional[date] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成日报

        Args:
            report_date: 报告日期
            data: 预收集的数据，None则自动收集

        Returns:
            生成结果
        """
        report_date = report_date or date.today()

        if data is None:
            data = self._collect_daily_data(report_date)

        try:
            if JINJA2_AVAILABLE and PDFKIT_AVAILABLE:
                pdf_path = self._render_pdf("daily_report.html", data, f'daily_{report_date.strftime("%Y%m%d")}')
            else:
                # 如果没有依赖，生成CSV
                pdf_path = self._generate_csv("daily", report_date, data)

            self._save_report_record("daily", report_date, str(pdf_path), "generated")
            return {
                "success": True,
                "report_path": str(pdf_path),
                "report_date": report_date.isoformat(),
                "report_type": "daily",
            }
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            self._save_report_record("daily", report_date, "", "failed")
            return {
                "success": False,
                "error": str(e),
            }

    def generate_monthly_report(
        self,
        year: int,
        month: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成月报

        Args:
            year: 年份
            month: 月份
            data: 预收集的数据

        Returns:
            生成结果
        """
        report_date = date(year, month, 1)

        if data is None:
            data = self._collect_monthly_data(year, month)

        try:
            if JINJA2_AVAILABLE and PDFKIT_AVAILABLE:
                pdf_path = self._render_pdf("monthly_report.html", data, f"monthly_{year}{month:02d}")
            else:
                pdf_path = self._generate_csv("monthly", report_date, data)

            self._save_report_record("monthly", report_date, str(pdf_path), "generated")
            return {
                "success": True,
                "report_path": str(pdf_path),
                "year": year,
                "month": month,
                "report_type": "monthly",
            }
        except Exception as e:
            logger.error(f"Failed to generate monthly report: {e}")
            self._save_report_record("monthly", report_date, "", "failed")
            return {
                "success": False,
                "error": str(e),
            }

    def generate_abnormal_trade_report(
        self,
        start_date: date,
        end_date: date,
        detection_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        生成异常交易报告

        Args:
            start_date: 开始日期
            end_date: 结束日期
            detection_result: 异常检测结果

        Returns:
            生成结果
        """
        data = {
            "start_date": start_date,
            "end_date": end_date,
            "detection_result": detection_result,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            if JINJA2_AVAILABLE and PDFKIT_AVAILABLE:
                filename = f'abnormal_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}'
                pdf_path = self._render_pdf("abnormal_trade_report.html", data, filename)
            else:
                pdf_path = self._generate_csv(
                    f'abnormal_{start_date.strftime("%Y%m%d")}',
                    date.today(),
                    data,
                )

            self._save_report_record("abnormal", start_date, str(pdf_path), "generated")
            return {
                "success": True,
                "report_path": str(pdf_path),
                "report_type": "abnormal",
            }
        except Exception as e:
            logger.error(f"Failed to generate abnormal trade report: {e}")
            self._save_report_record("abnormal", start_date, "", "failed")
            return {
                "success": False,
                "error": str(e),
            }

    def generate_quarterly_report(
        self,
        year: int,
        quarter: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成季度报告

        Args:
            year: 年份
            quarter: 季度（1-4）
            data: 预收集的数据

        Returns:
            生成结果
        """
        start_month = (quarter - 1) * 3 + 1
        report_date = date(year, start_month, 1)

        if data is None:
            data = self._collect_quarterly_data(year, quarter)

        try:
            if JINJA2_AVAILABLE and PDFKIT_AVAILABLE:
                pdf_path = self._render_pdf("quarterly_report.html", data, f"quarterly_{year}_q{quarter}")
            else:
                pdf_path = self._generate_csv(f"quarterly_{year}_q{quarter}", report_date, data)

            self._save_report_record("quarterly", report_date, str(pdf_path), "generated")
            return {
                "success": True,
                "report_path": str(pdf_path),
                "year": year,
                "quarter": quarter,
                "report_type": "quarterly",
            }
        except Exception as e:
            logger.error(f"Failed to generate quarterly report: {e}")
            self._save_report_record("quarterly", report_date, "", "failed")
            return {
                "success": False,
                "error": str(e),
            }

    def _collect_daily_data(self, report_date: date) -> Dict[str, Any]:
        """收集日报数据 - 需要外部提供数据，这里只定义结构"""
        return {
            "report_date": report_date,
            "report_date_str": report_date.strftime("%Y年%m月%d日"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # 子类覆盖实际收集
            "total_trades": 0,
            "total_volume": 0.0,
            "abnormal_trades": 0,
            "risk_events": 0,
            "user_statistics": {},
        }

    def _collect_monthly_data(self, year: int, month: int) -> Dict[str, Any]:
        """收集月报数据"""
        return {
            "year": year,
            "month": month,
            "month_str": f"{year}年{month}月",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_trades": 0,
            "total_volume": 0.0,
            "abnormal_trades": 0,
            "risk_events": 0,
            "compliance_rate": 1.0,
            "daily_stats": [],
        }

    def _collect_quarterly_data(self, year: int, quarter: int) -> Dict[str, Any]:
        """收集季度数据"""
        return {
            "year": year,
            "quarter": quarter,
            "quarter_str": f"{year}年第{quarter}季度",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_trades": 0,
            "total_volume": 0.0,
            "abnormal_trades": 0,
            "risk_events": 0,
            "compliance_rate": 1.0,
            "monthly_stats": [],
        }

    def _render_pdf(self, template_name: str, data: Dict[str, Any], filename: str) -> Path:
        """渲染HTML模板生成PDF"""
        if not JINJA2_AVAILABLE:
            raise RuntimeError("jinja2 is required for HTML template rendering")
        if not PDFKIT_AVAILABLE:
            raise RuntimeError("pdfkit is required for PDF generation")

        template = self._jinja_env.get_template(template_name)
        html_content = template.render(**data)

        output_path = self._report_output_dir / f"{filename}.pdf"
        pdfkit.from_string(html_content, str(output_path))
        return output_path

    def _generate_csv(self, report_type: str, report_date: date, data: Dict[str, Any]) -> Path:
        """生成CSV格式回退"""
        output_path = self._report_output_dir / f'{report_type}_{report_date.strftime("%Y%m%d")}.csv'
        df = pd.DataFrame([data])
        df.to_csv(output_path, index=False)
        return output_path

    def _save_report_record(
        self,
        report_type: str,
        report_date: date,
        path: str,
        status: str,
    ) -> None:
        """保存报表生成记录"""
        # 这里应该存储到数据库，简化版本只记录日志
        logger.info(f"Compliance report saved: type={report_type}, date={report_date}, path={path}, status={status}")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "jinja2_available": JINJA2_AVAILABLE,
            "pdfkit_available": PDFKIT_AVAILABLE,
            "template_dir": self._template_dir,
            "output_dir": str(self._report_output_dir),
        }
