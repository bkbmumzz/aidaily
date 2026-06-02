"""JSON 文件存储管理"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import DailyReport

logger = logging.getLogger(__name__)


class Storage:
    """按日期存储 JSON 数据"""

    def __init__(self, json_dir: Path, history_dir: Path | None = None):
        self.json_dir = json_dir
        self.history_dir = history_dir or json_dir.parent / "history"
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_daily_report(self, report: DailyReport) -> Path:
        """保存当日数据为 JSON

        Returns:
            保存的文件路径
        """
        filepath = self.json_dir / f"{report.date}.json"
        data = report.to_dict()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"已保存 JSON: {filepath}")
        return filepath

    def load_daily_report(self, date: str) -> dict | None:
        """加载指定日期的原始 JSON 数据"""
        filepath = self.json_dir / f"{date}.json"
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_available_dates(self, limit: int = 30) -> list[str]:
        """列出可用的日期列表（降序）"""
        json_files = sorted(self.json_dir.glob("*.json"), reverse=True)
        return [f.stem for f in json_files[:limit]]

    def update_summary(self, report: DailyReport) -> None:
        """更新汇总数据 history/summary.json

        用于首页展示最近趋势
        """
        summary_path = self.history_dir / "summary.json"

        # 读取现有汇总
        summary: dict = {}
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)

        # 更新今日数据
        dates = summary.get("dates", [])
        if report.date not in dates:
            dates.insert(0, report.date)

        # 只保留最近 90 天
        dates = dates[:90]

        # 统计数据
        repo_count = len(report.all_repos())
        issue_count = len(report.hot_issues) + len(report.hot_prs)

        summary["dates"] = dates
        summary["latest_date"] = report.date
        summary["latest_repo_count"] = repo_count
        summary["latest_issue_count"] = issue_count
        summary["updated_at"] = report.generated_at

        # 保存每个日期的简要统计
        daily_stats = summary.get("daily_stats", {})
        daily_stats[report.date] = {
            "repo_count": repo_count,
            "issue_count": issue_count,
            "trending_languages": list(report.trending_repos.keys()),
            "top_repos": [
                {"name": r.name, "stars": r.stars, "stars_today": r.stars_today}
                for r in list(report.trending_repos.get("daily", []))[:5]
            ],
        }
        summary["daily_stats"] = daily_stats

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"已更新汇总: {summary_path}")
