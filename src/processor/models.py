"""数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RepoInfo:
    """GitHub 仓库信息"""

    name: str  # "owner/repo"
    url: str  # "https://github.com/owner/repo"
    description: str = ""
    language: str | None = None
    stars: int = 0
    forks: int = 0
    stars_today: int | None = None  # Trending 特有
    trending_range: str | None = None  # "daily" | "weekly" | "monthly"
    trending_language: str | None = None
    created_at: str | None = None
    pushed_at: str | None = None
    topics: list[str] = field(default_factory=list)
    open_issues_count: int | None = None
    license: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def owner(self) -> str:
        return self.name.split("/")[0] if "/" in self.name else ""

    @property
    def repo(self) -> str:
        return self.name.split("/")[1] if "/" in self.name else self.name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "language": self.language,
            "stars": self.stars,
            "forks": self.forks,
            "stars_today": self.stars_today,
            "trending_range": self.trending_range,
            "trending_language": self.trending_language,
            "created_at": self.created_at,
            "pushed_at": self.pushed_at,
            "topics": self.topics,
            "open_issues_count": self.open_issues_count,
            "license": self.license,
            "fetched_at": self.fetched_at,
        }


@dataclass
class IssueInfo:
    """GitHub Issue/PR 信息"""

    title: str
    url: str
    type: str  # "issue" | "pr"
    state: str = "open"
    repo_name: str = ""
    repo_url: str = ""
    author: str = ""
    created_at: str = ""
    comments: int = 0
    reactions: int | None = None
    labels: list[str] = field(default_factory=list)
    body_preview: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "type": self.type,
            "state": self.state,
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "author": self.author,
            "created_at": self.created_at,
            "comments": self.comments,
            "reactions": self.reactions,
            "labels": self.labels,
            "body_preview": self.body_preview,
            "fetched_at": self.fetched_at,
        }


@dataclass
class DailyReport:
    """每日报告数据"""

    date: str  # "YYYY-MM-DD"
    trending_repos: dict[str, list[RepoInfo]] = field(default_factory=dict)
    # key: "daily", "python_daily", "weekly" 等
    fast_growing_repos: list[RepoInfo] = field(default_factory=list)
    new_high_star_repos: list[RepoInfo] = field(default_factory=list)
    hot_issues: list[IssueInfo] = field(default_factory=list)
    hot_prs: list[IssueInfo] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "trending_repos": {
                k: [r.to_dict() for r in v] for k, v in self.trending_repos.items()
            },
            "fast_growing_repos": [r.to_dict() for r in self.fast_growing_repos],
            "new_high_star_repos": [r.to_dict() for r in self.new_high_star_repos],
            "hot_issues": [i.to_dict() for i in self.hot_issues],
            "hot_prs": [i.to_dict() for i in self.hot_prs],
            "generated_at": self.generated_at,
        }

    def all_repos(self) -> list[RepoInfo]:
        """获取所有仓库的扁平列表（去重）"""
        seen: set[str] = set()
        result: list[RepoInfo] = []
        for repo_list in self.trending_repos.values():
            for repo in repo_list:
                if repo.name not in seen:
                    seen.add(repo.name)
                    result.append(repo)
        for repo in self.fast_growing_repos + self.new_high_star_repos:
            if repo.name not in seen:
                seen.add(repo.name)
                result.append(repo)
        return result
