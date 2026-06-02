from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    # GitHub API
    github_token: str = os.getenv("GITHUB_TOKEN", "")

    # 路径
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    reports_dir: Path = data_dir / "reports"
    json_dir: Path = data_dir / "json"
    history_dir: Path = data_dir / "history"
    docs_dir: Path = BASE_DIR / "docs"

    # 抓取配置
    trending_languages: list[str] = field(
        default_factory=lambda: [
            "", "python", "javascript", "typescript", "go", "rust", "java", "c++"
        ]
    )
    trending_ranges: list[str] = field(
        default_factory=lambda: ["daily", "weekly", "monthly"]
    )

    # API 配置
    api_base_url: str = "https://api.github.com"
    api_per_page: int = 30
    api_max_pages: int = 3

    # Rate limit
    requests_per_second: float = 1.0
    max_retries: int = 3
    retry_backoff: float = 2.0

    def __post_init__(self):
        # 确保关键目录存在
        for d in [self.data_dir, self.reports_dir, self.json_dir, self.history_dir, self.docs_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
