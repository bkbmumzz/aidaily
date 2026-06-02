"""去重逻辑"""

from __future__ import annotations

from .models import RepoInfo, IssueInfo


class Deduplicator:
    """基于名称的跨维度去重"""

    def __init__(self):
        self._seen_repos: set[str] = set()
        self._seen_issues: set[str] = set()

    def dedup_repos(self, repos: list[RepoInfo]) -> list[RepoInfo]:
        """去重仓库，保留首次出现"""
        result: list[RepoInfo] = []
        for repo in repos:
            if repo.name not in self._seen_repos:
                self._seen_repos.add(repo.name)
                result.append(repo)
        return result

    def dedup_issues(self, issues: list[IssueInfo]) -> list[IssueInfo]:
        """去重 Issue/PR"""
        result: list[IssueInfo] = []
        for issue in issues:
            if issue.url not in self._seen_issues:
                self._seen_issues.add(issue.url)
                result.append(issue)
        return result

    def reset(self) -> None:
        """重置去重状态"""
        self._seen_repos.clear()
        self._seen_issues.clear()

    @property
    def seen_repos_count(self) -> int:
        return len(self._seen_repos)
