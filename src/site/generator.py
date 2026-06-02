"""静态网站生成器"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..processor.models import DailyReport
from ..processor.storage import Storage

logger = logging.getLogger(__name__)


def format_number(value) -> str:
    """格式化数字"""
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


class SiteGenerator:
    """生成静态网站"""

    def __init__(self, base_dir: Path, docs_dir: Path, json_dir: Path, history_dir: Path):
        self.base_dir = base_dir
        self.docs_dir = docs_dir
        self.json_dir = json_dir
        self.history_dir = history_dir

        template_dir = base_dir / "src" / "site" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )
        self.env.filters["format_number"] = format_number
        self.env.filters["truncate"] = lambda s, n: s[:n] + "..." if len(s) > n else s

        self.storage = Storage(json_dir, history_dir)

        # GitHub Pages 部署时 base_url 可能是 /repo-name
        # 本地预览用相对路径，部署时改为绝对路径
        self.base_url = "."
        self.static_url = "./static"

    def generate_all(self, report: DailyReport) -> None:
        """生成所有页面"""
        logger.info("开始生成静态网站...")

        # 确保输出目录存在
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "daily").mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "projects").mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "static").mkdir(parents=True, exist_ok=True)

        self._generate_index(report)
        self._generate_daily_page(report)
        self._generate_project_pages(report)
        self._copy_static_assets()

        logger.info(f"静态网站生成完成: {self.docs_dir}")

    def _render(self, template_name: str, **context) -> str:
        """渲染模板"""
        template = self.env.get_template(template_name)
        context.setdefault("base_url", self.base_url)
        context.setdefault("static_url", self.static_url)
        return template.render(**context)

    def _write(self, path: Path, content: str) -> None:
        """写入文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _generate_index(self, report: DailyReport) -> None:
        """生成首页"""
        available_dates = self.storage.list_available_dates(30)

        # 今日 Trending Top 5
        top_repos = []
        for repo in report.trending_repos.get("daily", [])[:5]:
            top_repos.append({
                "name": repo.name,
                "url": repo.url,
                "slug": repo.name.replace("/", "--"),
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stars,
                "stars_today": repo.stars_today,
                "forks": repo.forks,
            })

        html = self._render(
            "index.html",
            report=report,
            top_repos=top_repos,
            available_dates=available_dates,
        )
        self._write(self.docs_dir / "index.html", html)
        logger.info("已生成首页: index.html")

    def _generate_daily_page(self, report: DailyReport) -> None:
        """生成每日详情页"""
        html = self._render("daily.html", report=report)
        self._write(self.docs_dir / "daily" / f"{report.date}.html", html)
        logger.info(f"已生成每日页面: daily/{report.date}.html")

    def _generate_project_pages(self, report: DailyReport) -> None:
        """生成项目详情页"""
        all_repos = report.all_repos()

        for repo in all_repos:
            slug = repo.name.replace("/", "--")

            # 查找该项目在所有维度的出现记录
            appearances = self._find_appearances(repo, report)

            html = self._render(
                "project.html",
                repo=repo,
                appearances=appearances,
            )
            self._write(self.docs_dir / "projects" / f"{slug}.html", html)

        logger.info(f"已生成 {len(all_repos)} 个项目详情页")

    def _find_appearances(self, repo, report: DailyReport) -> list[dict]:
        """查找项目在报告各维度中的出现记录"""
        appearances = []
        target_name = repo.name

        # 检查 trending
        for key, repos in report.trending_repos.items():
            for i, r in enumerate(repos):
                if r.name == target_name:
                    appearances.append({
                        "date": report.date,
                        "source": f"Trending ({key})",
                        "rank": i + 1,
                        "stars": r.stars,
                        "stars_today": r.stars_today,
                    })

        # 检查 fast growing
        for i, r in enumerate(report.fast_growing_repos):
            if r.name == target_name:
                appearances.append({
                    "date": report.date,
                    "source": "Star 增长最快",
                    "rank": i + 1,
                    "stars": r.stars,
                    "stars_today": None,
                })

        # 检查 new high star
        for i, r in enumerate(report.new_high_star_repos):
            if r.name == target_name:
                appearances.append({
                    "date": report.date,
                    "source": "新创建高星项目",
                    "rank": i + 1,
                    "stars": r.stars,
                    "stars_today": None,
                })

        return appearances

    def _copy_static_assets(self) -> None:
        """复制 CSS/JS 到 docs/static/"""
        dst_dir = self.docs_dir / "static"

        # 复制 src/site/static/ 下的文件
        src_dir = self.base_dir / "src" / "site" / "static"
        if src_dir.exists():
            for f in src_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, dst_dir / f.name)
                    logger.debug(f"复制静态资源: {f.name}")

        # 复制项目根目录的 tailwindcss.js
        tailwind_src = self.base_dir / "tailwindcss.js"
        if tailwind_src.exists():
            shutil.copy2(tailwind_src, dst_dir / "tailwindcss.js")
            logger.debug("复制 tailwindcss.js")
