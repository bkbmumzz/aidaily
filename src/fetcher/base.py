"""所有抓取器的基类"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import Settings

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """提供 HTTP 客户端、重试、错误处理"""

    def __init__(self, settings: Settings | None = None):
        from config.settings import settings as default_settings

        self.settings = settings or default_settings
        self.client: httpx.Client = self._create_client()

    def _create_client(self) -> httpx.Client:
        """创建带默认 headers 的 HTTP 客户端"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "aidaily/0.1.0",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return httpx.Client(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        before_sleep=lambda state: logger.warning(
            f"请求失败，第 {state.attempt_number} 次重试: {state.outcome.exception()}"
        ),
    )
    def _request(self, url: str, params: dict | None = None) -> httpx.Response:
        """带重试的 HTTP GET 请求"""
        logger.debug(f"GET {url} params={params}")
        response = self.client.get(url, params=params)

        # 处理 rate limit
        if response.status_code in (403, 429):
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                from .rate_limiter import RateLimiter

                limiter = RateLimiter(self.settings.requests_per_second)
                limiter.wait_for_reset(int(reset))
                # 重试一次
                response = self.client.get(url, params=params)

        response.raise_for_status()
        return response

    def _check_rate_limit(self, response: httpx.Response) -> None:
        """检查并记录 rate limit 状态"""
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        if remaining and limit:
            logger.debug(f"Rate limit: {remaining}/{limit} 剩余")

    @abstractmethod
    def fetch(self, **kwargs) -> list:
        """子类实现具体抓取逻辑"""
        ...

    def close(self) -> None:
        """关闭 HTTP 客户端"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
