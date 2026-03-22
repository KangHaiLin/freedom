"""
回测报告生成器
生成HTML/CSV/PNG回测结果报告
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from src.strategy_research.base import BacktestResult


def generate_json_report(result: BacktestResult) -> str:
    """生成JSON格式报告"""
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def generate_text_report(result: BacktestResult) -> str:
    """生成文本格式报告"""
    lines = []
    lines.append(f"回测报告: {result.strategy_name}")
    lines.append("=" * 50)
    lines.append(f"初始资金: {result.initial_capital:.2f}")
    lines.append(f"最终资金: {result.final_capital:.2f}")
    lines.append(f"总收益: {result.total_pnl_pct:.2f}%")
    lines.append(f"年化收益: {result.annualized_return:.2f}%")
    lines.append(f"夏普比率: {result.sharpe_ratio:.2f}")
    lines.append(f"最大回撤: {result.max_drawdown:.2f}%")
    lines.append(f"胜率: {result.win_rate:.1f}%")
    lines.append(f"盈亏比: {result.profit_loss_ratio:.2f}")
    lines.append(f"总交易次数: {result.total_trades}")
    lines.append(f"盈利交易: {result.winning_trades}")
    lines.append(f"亏损交易: {result.losing_trades}")
    lines.append(f"平均持有天数: {result.avg_holding_days:.1f}")
    lines.append(f"年均换手率: {result.turnover_rate:.1f}%")
    lines.append("")
    lines.append("生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return "\n".join(lines)


def generate_html_report(result: BacktestResult, include_charts: bool = True) -> str:
    """生成HTML格式报告"""

    # 准备数据
    daily_data = []
    for ds in result.daily_stats:
        if hasattr(ds.date, "isoformat"):
            date_str = ds.date.isoformat()
        else:
            date_str = str(ds.date)
        daily_data.append(
            {
                "date": date_str,
                "total_assets": ds.total_assets,
                "daily_pnl": ds.daily_pnl,
            }
        )

    daily_json = json.dumps(daily_data, ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>回测报告 - {result.strategy_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #f5f5f5; padding: 15px; border-radius: 8px; }}
        .metric-label {{ font-size: 0.9em; color: #666; }}
        .metric-value {{ font-size: 1.4em; font-weight: bold; color: #333; margin-top: 5px; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        #chart div {{ height: 400px; margin: 20px 0; }}
    </style>
</head>
<body>
<div class="container">
    <h1>回测报告: {result.strategy_name}</h1>

    <div class="metrics">
        <div class="metric-card">
            <div class="metric-label">初始资金</div>
            <div class="metric-value">{result.initial_capital:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">最终资金</div>
            <div class="metric-value">{result.final_capital:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">总收益</div>
            <div class="metric-value {'positive' if result.total_pnl_pct > 0 else 'negative'}">{result.total_pnl_pct:+.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">年化收益</div>
            <div class="metric-value {'positive' if result.annualized_return > 0 else 'negative'}">{result.annualized_return:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">夏普比率</div>
            <div class="metric-value">{result.sharpe_ratio:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">最大回撤</div>
            <div class="metric-value negative">{result.max_drawdown:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{result.win_rate:.1f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">盈亏比</div>
            <div class="metric-value">{result.profit_loss_ratio:.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">总交易次数</div>
            <div class="metric-value">{result.total_trades}</div>
        </div>
    </div>
"""

    if include_charts:
        html += (
            """
    <h2>权益曲线</h2>
    <div id="equity-chart"></div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const data = """
            + daily_json
            + """;
        const ctx = document.getElementById('equity-chart').getContext('2d');
        const labels = data.map(d => d.date.slice(0, 10));
        const values = data.map(d => d.total_assets);

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '总资产',
                    data: values,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '累计权益曲线'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    </script>
"""
        )

    html += """
</div>
</body>
</html>
"""

    return html


def save_report(
    result: BacktestResult,
    output_path: str,
    format: str = "html",
) -> Dict[str, Any]:
    """
    保存回测报告到文件

    Args:
        result: 回测结果
        output_path: 输出路径
        format: 格式 html/json/text

    Returns:
        保存结果
    """
    if format == "html":
        content = generate_html_report(result)
        content_type = "text/html"
    elif format == "json":
        content = generate_json_report(result)
        content_type = "application/json"
    elif format == "text":
        content = generate_text_report(result)
        content_type = "text/plain"
    else:
        return {"success": False, "error": f"Unknown format {format}"}

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "path": output_path,
            "format": format,
            "content_type": content_type,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
