"""Markdown 报告构建器"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..processor.models import DailyReport

logger = logging.getLogger(__name__)


def format_number(value) -> str:
    """Jinja2 过滤器: 格式化数字为人类可读形式"""
    if value is None:
        return "-"
    try:
        num = int(value)
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)
    except (ValueError, TypeError):
        return str(value)


class MarkdownBuilder:
    """生成每日 Markdown 报告"""

    def __init__(self, template_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
        )
        # 注册自定义过滤器
        self.env.filters["format_number"] = format_number
        self.env.filters["truncate"] = lambda s, n: s[:n] + "..." if len(s) > n else s

    def build(self, report: DailyReport) -> str:
        """生成完整 Markdown 报告"""
        template = self.env.get_template("daily_report.md.j2")
        return template.render(report=report, date_str=report.date)

    def save(self, content: str, output_path: Path) -> Path:
        """保存 Markdown 文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"已保存 Markdown 报告: {output_path}")
        return output_path
