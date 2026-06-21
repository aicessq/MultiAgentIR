"""Document fetcher specification.

DocumentFetcher is responsible for:
1. Downloading full content from URLs
2. Extracting and cleaning text
3. Computing canonical URL and content hash
4. Detecting language and word count

Key constraint: NOT for evidence extraction (that's a separate step)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import SourceTier


class FetchRequest(BaseModel):
    """Request to fetch documents."""

    urls: list[str] = Field(default_factory=list)
    max_concurrent: int = 5
    timeout_per_url_seconds: float = 30.0
    max_content_size_bytes: int = 10 * 1024 * 1024  # 10MB
    max_redirects: int = 5
    user_agent: str = "Mozilla/5.0 (compatible; ResearchBot/1.0)"
    respect_robots_txt: bool = True
    extract_metadata: bool = True
    clean_html: bool = True


class FetchResult(BaseModel):
    """Result of fetching a single URL."""

    url: str
    canonical_url: str
    success: bool
    status_code: int | None = None
    error_message: str | None = None
    title: str | None = None
    content: str | None = None
    content_hash: str | None = None
    word_count: int | None = None
    language: str | None = None
    publish_date: datetime | None = None
    fetch_time_ms: float = 0.0
    content_type: str | None = None
    metadata: dict = Field(default_factory=dict)
    blocked_reason: str | None = None  # e.g., "robots_txt", "private_ip", "paywall"


class FetchResponse(BaseModel):
    """Response from DocumentFetcher."""

    results: list[FetchResult] = Field(default_factory=list)
    successful_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    total_time_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)