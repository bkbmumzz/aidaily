"""GitHub REST API 客户端"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .base import BaseFetcher
from .rate_limiter import RateLimiter
from ..processor.models import RepoInfo, IssueInfo

logger = logging.getLogger(__name__)


class GitHubAPIFetcher(BaseFetcher):
    """通过 GitHub REST API 抓取数据"""

    def __init__(self, settings=None):
        super().__init__(settings)
        self.rate_limiter = RateLimiter(self.settings.requests_per_second)

    def fetch_fast_growing_repos(
        self,
        min_stars: int = 100,
        days: int = 7,
        language: str = "",
        limit: int = 30,
    ) -> list[RepoInfo]:
        """获取 Star 增长最快的项目

        查询过去 N 天内有 push 活动且 star 数较高的项目，按 star 降序
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query_parts = [f"stars:>{min_stars}", f"pushed:>{since_date}"]
        if language:
            query_parts.append(f"language:{language}")

        query = " ".join(query_parts)
        logger.info(f"查询 Star 增长最快: {query}")
        return self._search_repos(query, sort="stars", limit=limit)

    def fetch_new_high_star_repos(
        self,
        days: int = 30,
        min_stars: int = 100,
        language: str = "",
        limit: int = 30,
    ) -> list[RepoInfo]:
        """获取最近创建的高星项目"""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query_parts = [f"created:>{since_date}", f"stars:>{min_stars}"]
        if language:
            query_parts.append(f"language:{language}")

        query = " ".join(query_parts)
        logger.info(f"查询新创建高星项目: {query}")
        return self._search_repos(query, sort="stars", limit=limit)

    def fetch_hot_issues(
        self,
        days: int = 7,
        min_comments: int = 10,
        limit: int = 20,
    ) -> list[IssueInfo]:
        """获取热门 Issue"""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = f"type:issue comments:>{min_comments} created:>{since_date}"
        logger.info(f"查询热门 Issue: {query}")
        return self._search_issues(query, sort="comments", limit=limit)

    def fetch_hot_prs(
        self,
        days: int = 7,
        min_comments: int = 5,
        limit: int = 20,
    ) -> list[IssueInfo]:
        """获取热门 PR"""
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = f"type:pr comments:>{min_comments} created:>{since_date}"
        logger.info(f"查询热门 PR: {query}")
        return self._search_issues(query, sort="comments", limit=limit)

    def _search_repos(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        limit: int = 30,
    ) -> list[RepoInfo]:
        """通用仓库搜索"""
        repos: list[RepoInfo] = []
        per_page = min(self.settings.api_per_page, limit)
        max_pages = min(self.settings.api_max_pages, (limit // per_page) + 1)

        for page in range(1, max_pages + 1):
            self.rate_limiter.acquire()
            url = f"{self.settings.api_base_url}/search/repositories"
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": per_page,
                "page": page,
            }

            try:
                response = self._request(url, params=params)
                self._check_rate_limit(response)
                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                for item in items:
                    repos.append(self._parse_repo_item(item))

                # 检查是否还有更多数据
                total_count = data.get("total_count", 0)
                if len(repos) >= total_count or len(repos) >= limit:
                    break

            except Exception as e:
                logger.error(f"搜索仓库失败 (page {page}): {e}")
                break

        return repos[:limit]

    def _search_issues(
        self,
        query: str,
        sort: str = "comments",
        order: str = "desc",
        limit: int = 20,
    ) -> list[IssueInfo]:
        """通用 issue/PR 搜索"""
        issues: list[IssueInfo] = []
        per_page = min(self.settings.api_per_page, limit)

        self.rate_limiter.acquire()
        url = f"{self.settings.api_base_url}/search/issues"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
        }

        try:
            response = self._request(url, params=params)
            self._check_rate_limit(response)
            data = response.json()
            items = data.get("items", [])

            for item in items:
                issues.append(self._parse_issue_item(item))

        except Exception as e:
            logger.error(f"搜索 issue 失败: {e}")

        return issues[:limit]

    def _parse_repo_item(self, item: dict) -> RepoInfo:
        """将 API 返回的 repo JSON 转为 RepoInfo"""
        return RepoInfo(
            name=item.get("full_name", ""),
            url=item.get("html_url", ""),
            description=item.get("description", "") or "",
            language=item.get("language"),
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            created_at=item.get("created_at"),
            pushed_at=item.get("pushed_at"),
            topics=item.get("topics", []),
            open_issues_count=item.get("open_issues_count"),
            license=item.get("license", {}).get("spdx_id") if item.get("license") else None,
        )

    def _parse_issue_item(self, item: dict) -> IssueInfo:
        """将 API 返回的 issue JSON 转为 IssueInfo"""
        # 从 issue URL 中提取仓库名
        repo_url = item.get("repository_url", "")
        repo_name = repo_url.replace("https://api.github.com/repos/", "") if repo_url else ""
        repo_html_url = f"https://github.com/{repo_name}" if repo_name else ""

        # 判断是 issue 还是 PR
        item_type = "pr" if "pull_request" in item else "issue"

        # body 预览
        body = item.get("body", "") or ""
        body_preview = body[:200] + "..." if len(body) > 200 else body

        return IssueInfo(
            title=item.get("title", ""),
            url=item.get("html_url", ""),
            type=item_type,
            state=item.get("state", "open"),
            repo_name=repo_name,
            repo_url=repo_html_url,
            author=item.get("user", {}).get("login", ""),
            created_at=item.get("created_at", ""),
            comments=item.get("comments", 0),
            reactions=item.get("reactions", {}).get("total_count") if item.get("reactions") else None,
            labels=[label.get("name", "") for label in item.get("labels", [])],
            body_preview=body_preview or None,
        )

    def fetch(self, **kwargs) -> list:
        """BaseFetcher 抽象方法实现"""
        return []
