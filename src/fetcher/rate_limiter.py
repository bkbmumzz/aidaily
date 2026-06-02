"""令牌桶限速器"""

from __future__ import annotations

import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """简单的令牌桶限速器"""

    def __init__(self, rate: float = 1.0):
        """
        Args:
            rate: 每秒允许的请求数
        """
        self.rate = rate
        self.min_interval = 1.0 / rate if rate > 0 else 0
        self._last_request: float = 0.0

    def acquire(self) -> None:
        """等待直到可以发起请求"""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiter: 等待 {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request = time.monotonic()

    def wait_for_reset(self, reset_time: int) -> None:
        """等待 GitHub API rate limit 重置

        Args:
            reset_time: Unix 时间戳，rate limit 重置时间
        """
        now = time.time()
        wait_seconds = max(reset_time - now + 1, 0)  # 多等 1 秒
        if wait_seconds > 0:
            logger.warning(f"Rate limit 达到上限，等待 {wait_seconds:.0f}s 至重置")
            time.sleep(wait_seconds)
