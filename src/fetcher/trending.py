"""GitHub Trending 页面爬虫"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Any

from bs4 import BeautifulSoup

from .base import BaseFetcher
from ..processor.models import RepoInfo

logger = logging.getLogger(__name__)


class TrendingFetcher(BaseFetcher):
    """爬取 GitHub Trending 页面"""

    TRENDING_URL = "https://github.com/trending"

    def fetch(self, language: str = "", since: str = "daily") -> list[RepoInfo]:
        """抓取指定语言和时间范围的 trending 列表

        Args:
            language: 编程语言，空字符串表示所有语言
            since: "daily" | "weekly" | "monthly"

        Returns:
            RepoInfo 列表
        """
        url = self._build_url(language, since)
        lang_label = language or "all"
        logger.info(f"正在抓取 Trending: {lang_label} / {since}")

        try:
            # 随机延迟，避免被封
            time.sleep(random.uniform(1.0, 3.0))
            response = self._request(url)
            repos = self._parse_page(response.text, since, language)
            logger.info(f"Trending {lang_label}/{since}: 获取到 {len(repos)} 个项目")
            return repos
        except Exception as e:
            logger.error(f"抓取 Trending {lang_label}/{since} 失败: {e}")
            return []

    def _build_url(self, language: str, since: str) -> str:
        """构造 trending URL

        示例:
            https://github.com/trending
            https://github.com/trending/python?since=weekly
        """
        base = self.TRENDING_URL
        if language:
            base = f"{base}/{language}"
        return f"{base}?since={since}"

    def _parse_page(
        self, html: str, since: str, language: str | None = None
    ) -> list[RepoInfo]:
        """解析 trending 页面 HTML

        GitHub Trending 页面结构:
        - 每个 repo 在 <article class="Box-row"> 中
        - 仓库名在 h2 > a 中，href 格式为 /owner/repo
        - 描述在 <p> 标签中
        - 语言、star、fork 在浮动 div 中
        - 今日 star 数在最后
        """
        soup = BeautifulSoup(html, "html.parser")
        repos: list[RepoInfo] = []

        # GitHub 使用 article.Box-row 或 article[data-testid="repos-list-item"]
        articles = soup.select("article.Box-row")
        if not articles:
            # 备用选择器
            articles = soup.select("article")

        for article in articles:
            try:
                repo = self._parse_article(article, since, language)
                if repo:
                    repos.append(repo)
            except Exception as e:
                logger.warning(f"解析单个 trending 项目失败: {e}")
                continue

        return repos

    def _parse_article(
        self, article: Any, since: str, language: str | None = None
    ) -> RepoInfo | None:
        """解析单个 trending 项目"""
        # 提取仓库名称
        name_el = article.select_one("h2 a")
        if not name_el:
            return None

        # href 格式: /owner/repo
        href = name_el.get("href", "")
        if not href:
            return None
        name = href.strip("/")

        # 提取描述
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # 提取编程语言
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        repo_language = lang_el.get_text(strip=True) if lang_el else None
        if not repo_language:
            # 备用: 找带有颜色圆点的 span
            for span in article.select("span"):
                text = span.get_text(strip=True)
                # 语言通常在颜色圆点后面
                if span.select_one(".repo-language-color") or span.get(
                    "itemprop"
                ) == "programmingLanguage":
                    repo_language = text
                    break

        # 提取 star 和 fork 数
        stars = self._parse_count(article, "star")
        forks = self._parse_count(article, "fork")

        # 提取今日/本周/本月 star 数
        stars_today = self._parse_stars_period(article)

        return RepoInfo(
            name=name,
            url=f"https://github.com/{name}",
            description=description,
            language=repo_language,
            stars=stars,
            forks=forks,
            stars_today=stars_today,
            trending_range=since,
            trending_language=language or None,
        )

    def _parse_count(self, article: Any, kind: str) -> int:
        """从 article 中解析 star/fork 数"""
        # 尝试多种选择器
        selectors = [
            f'a[href*="/stargazers"]',
            f'a[href*="/forks"]',
            f'svg.octicon-{kind}',
        ]
        if kind == "star":
            # Star 链接
            for link in article.select("a"):
                href = link.get("href", "")
                if "/stargazers" in href:
                    text = link.get_text(strip=True).replace(",", "")
                    try:
                        return int(text)
                    except ValueError:
                        pass
        elif kind == "fork":
            for link in article.select("a"):
                href = link.get("href", "")
                if "/forks" in href or "/network/members" in href:
                    text = link.get_text(strip=True).replace(",", "")
                    try:
                        return int(text)
                    except ValueError:
                        pass

        # 备用: 遍历所有 SVG 图标旁的文本
        for svg in article.select("svg"):
            classes = " ".join(svg.get("class", []))
            if kind == "star" and "octicon-star" in classes:
                parent = svg.parent
                if parent:
                    text = parent.get_text(strip=True).replace(",", "")
                    numbers = re.findall(r"\d+", text)
                    if numbers:
                        return int(numbers[-1])
            elif kind == "fork" and "octicon-repo-forked" in classes:
                parent = svg.parent
                if parent:
                    text = parent.get_text(strip=True).replace(",", "")
                    numbers = re.findall(r"\d+", text)
                    if numbers:
                        return int(numbers[-1])
        return 0

    def _parse_stars_period(self, article: Any) -> int | None:
        """解析时间段内的 star 数，如 '3,086 stars today'"""
        text = article.get_text()
        patterns = [
            r"([\d,]+)\s+stars?\s+(?:today|this\s+week|this\s+month)",
            r"([\d,]+)\s+stars?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None
