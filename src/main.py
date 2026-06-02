"""aidaily 主入口 - 编排所有抓取、生成流程"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# 确保 aidaily 根目录在 sys.path 中
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings
from src.fetcher.trending import TrendingFetcher
from src.fetcher.github_api import GitHubAPIFetcher
from src.processor.models import DailyReport
from src.processor.dedup import Deduplicator
from src.processor.storage import Storage
from src.reporter.markdown_builder import MarkdownBuilder
from src.site.generator import SiteGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aidaily")


def run(trending_only: bool = False):
    """主流程

    Args:
        trending_only: 仅抓取 Trending（跳过 API 调用，不需要 token）
    """
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"{'='*60}")
    logger.info(f"开始抓取 {today} 的数据")
    logger.info(f"{'='*60}")

    # 1. 初始化组件
    storage = Storage(settings.json_dir, settings.history_dir)
    dedup = Deduplicator()
    trending_repos: dict[str, list] = {}
    fast_growing: list = []
    new_high_star: list = []
    hot_issues: list = []
    hot_prs: list = []

    # 2. 抓取 GitHub Trending
    with TrendingFetcher(settings) as fetcher:
        for lang in settings.trending_languages:
            for since in settings.trending_ranges:
                key = f"{lang}_{since}" if lang else since
                repos = fetcher.fetch(language=lang, since=since)
                trending_repos[key] = dedup.dedup_repos(repos)
                logger.info(f"  Trending {key}: {len(repos)} 个项目")

    # 3. 如果不是 trending_only 模式，抓取 API 数据
    if not trending_only and settings.github_token:
        with GitHubAPIFetcher(settings) as api_fetcher:
            # Star 增长最快
            fast_growing = api_fetcher.fetch_fast_growing_repos(
                min_stars=100, days=7, limit=30
            )
            fast_growing = dedup.dedup_repos(fast_growing)
            logger.info(f"  Star 增长最快: {len(fast_growing)} 个项目")

            # 新创建的高星项目
            new_high_star = api_fetcher.fetch_new_high_star_repos(
                days=30, min_stars=100, limit=30
            )
            new_high_star = dedup.dedup_repos(new_high_star)
            logger.info(f"  新创建高星项目: {len(new_high_star)} 个项目")

            # 热门 Issue
            hot_issues = api_fetcher.fetch_hot_issues(days=7, min_comments=10, limit=20)
            hot_issues = dedup.dedup_issues(hot_issues)
            logger.info(f"  热门 Issue: {len(hot_issues)} 条")

            # 热门 PR
            hot_prs = api_fetcher.fetch_hot_prs(days=7, min_comments=5, limit=20)
            hot_prs = dedup.dedup_issues(hot_prs)
            logger.info(f"  热门 PR: {len(hot_prs)} 条")
    elif not trending_only:
        logger.warning("未设置 GITHUB_TOKEN，跳过 API 数据抓取")
        logger.warning("请设置环境变量: export GITHUB_TOKEN=your_token")

    # 4. 组装报告
    report = DailyReport(
        date=today,
        trending_repos=trending_repos,
        fast_growing_repos=fast_growing,
        new_high_star_repos=new_high_star,
        hot_issues=hot_issues,
        hot_prs=hot_prs,
    )

    # 5. 存储 JSON
    storage.save_daily_report(report)
    storage.update_summary(report)

    # 6. 生成 Markdown 报告
    template_dir = settings.base_dir / "src" / "reporter" / "templates"
    md_builder = MarkdownBuilder(template_dir)
    md_content = md_builder.build(report)
    md_builder.save(md_content, settings.reports_dir / f"{today}.md")

    # 7. 生成静态网站
    site_gen = SiteGenerator(
        base_dir=settings.base_dir,
        docs_dir=settings.docs_dir,
        json_dir=settings.json_dir,
        history_dir=settings.history_dir,
    )
    site_gen.generate_all(report)

    # 8. 输出汇总
    total_repos = len(report.all_repos())
    logger.info(f"{'='*60}")
    logger.info(f"完成! 共 {total_repos} 个项目")
    logger.info(f"  Markdown: data/reports/{today}.md")
    logger.info(f"  JSON:     data/json/{today}.json")
    logger.info(f"  网站:     docs/index.html")
    logger.info(f"{'='*60}")

    return report


if __name__ == "__main__":
    # 支持 --trending-only 参数仅抓取 Trending
    trending_only = "--trending-only" in sys.argv
    run(trending_only=trending_only)
