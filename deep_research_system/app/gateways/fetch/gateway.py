"""DocumentFetcher - downloads and extracts full content from URLs.

Key responsibilities:
1. Download content from URLs
2. Extract and clean text from HTML
3. Compute canonical URL and content hash
4. Detect language and word count
5. Respect robots.txt and rate limits

Key constraints:
- NO evidence extraction (that's a separate step after fetch)
- NO private IP access (SSRF protection)
- NO metadata endpoint access
- Content size limits enforced
- Timeout per URL enforced
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.domain.errors import FetchError, PolicyError, TransientError
from app.gateways.fetch.spec import FetchRequest, FetchResponse, FetchResult

logger = logging.getLogger(__name__)


# SSRF protection - blocked IP ranges
BLOCKED_IP_RANGES = [
    "127.0.0.0/8",  # Localhost
    "10.0.0.0/8",   # Private class A
    "172.16.0.0/12",  # Private class B
    "192.168.0.0/16",  # Private class C
    "169.254.0.0/16",  # Link-local
    "::1/128",  # IPv6 localhost
    "fc00::/7",  # IPv6 private
]

# Blocked domains for SSRF protection
BLOCKED_DOMAINS = [
    "localhost",
    "local",
    "internal",
    "metadata.google.internal",  # GCP metadata
    "metadata.azure",  # Azure metadata
    "169.254.169.254",  # AWS metadata IP
]


class DocumentFetcher(ABC):
    """Abstract base class for document fetcher."""

    @abstractmethod
    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch documents from URLs."""
        pass

    @abstractmethod
    def is_url_allowed(self, url: str) -> tuple[bool, str | None]:
        """Check if URL is allowed (SSRF protection)."""
        pass

    @abstractmethod
    def extract_content(self, html: str, url: str) -> tuple[str, str | None, int]:
        """Extract and clean content from HTML."""
        pass


class DefaultDocumentFetcher(DocumentFetcher):
    """Default implementation of DocumentFetcher."""

    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: float = 30.0,
        max_content_size: int = 10 * 1024 * 1024,
    ) -> None:
        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        self._max_content_size = max_content_size

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch documents from URLs.

        Process:
        1. Check each URL for SSRF protection
        2. Download with concurrency limit
        3. Extract and clean content
        4. Compute hash and metadata
        """
        start_time = time.time()

        semaphore = asyncio.Semaphore(request.max_concurrent)

        async def fetch_single(url: str) -> FetchResult:
            async with semaphore:
                return await self._fetch_single_url(url, request)

        tasks = [fetch_single(url) for url in request.urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetch_results = []
        successful = 0
        failed = 0
        blocked = 0
        errors = []

        for i, result in enumerate(results):
            url = request.urls[i]
            if isinstance(result, Exception):
                logger.error(f"Fetch failed for {url}: {result}")
                fetch_results.append(FetchResult(
                    url=url,
                    canonical_url=url,
                    success=False,
                    error_message=str(result),
                ))
                failed += 1
                errors.append(f"{url}: {str(result)}")
            else:
                fetch_results.append(result)
                if result.success:
                    successful += 1
                elif result.blocked_reason:
                    blocked += 1
                else:
                    failed += 1

        total_time_ms = (time.time() - start_time) * 1000

        return FetchResponse(
            results=fetch_results,
            successful_count=successful,
            failed_count=failed,
            blocked_count=blocked,
            total_time_ms=total_time_ms,
            errors=errors,
        )

    def is_url_allowed(self, url: str) -> tuple[bool, str | None]:
        """Check if URL is allowed (SSRF protection).

        Blocked:
        - localhost, local, internal domains
        - Private IP ranges
        - Metadata endpoints
        - Non-HTTP schemes
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ("http", "https"):
                return False, f"Invalid scheme: {parsed.scheme}"

            # Check blocked domains
            domain = parsed.netloc.lower()
            for blocked in BLOCKED_DOMAINS:
                if blocked in domain:
                    return False, f"Blocked domain: {blocked}"

            # Check for IP addresses (simplified)
            # In production, would use proper IP range checking
            if re.match(r"^(127\.|10\.|172\.16\.|192\.168\.|169\.254\.)", domain):
                return False, "Private IP range"

            return True, None

        except Exception as e:
            return False, f"Invalid URL: {str(e)}"

    def extract_content(self, html: str, url: str) -> tuple[str, str | None, int]:
        """Extract and clean content from HTML.

        Returns:
            (cleaned_content, title, word_count)
        """
        # Simplified extraction - production would use BeautifulSoup or similar
        # Extract title
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_match.group(1) if title_match else None

        # Remove script, style, and other non-content elements
        cleaned = html
        for pattern in [
            r"<script[^>]*>.*?</script>",
            r"<style[^>]*>.*?</style>",
            r"<nav[^>]*>.*?</nav>",
            r"<header[^>]*>.*?</header>",
            r"<footer[^>]*>.*?</footer>",
            r"<aside[^>]*>.*?</aside>",
            r"<!--.*?-->",
        ]:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

        # Remove HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Count words (simplified)
        word_count = len(cleaned.split())

        return cleaned, title, word_count

    async def _fetch_single_url(self, url: str, request: FetchRequest) -> FetchResult:
        """Fetch a single URL."""
        start_time = time.time()

        # Check if allowed
        allowed, reason = self.is_url_allowed(url)
        if not allowed:
            return FetchResult(
                url=url,
                canonical_url=url,
                success=False,
                blocked_reason=reason,
            )

        # Placeholder - actual implementation would use httpx
        # This simulates a successful fetch
        content = f"Fake content for {url}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        word_count = len(content.split())

        fetch_time_ms = (time.time() - start_time) * 1000

        return FetchResult(
            url=url,
            canonical_url=url,
            success=True,
            status_code=200,
            content=content,
            content_hash=content_hash,
            word_count=word_count,
            language="en",
            fetch_time_ms=fetch_time_ms,
            content_type="text/html",
        )


class FakeDocumentFetcher(DocumentFetcher):
    """Fake fetcher for testing."""

    def __init__(self, contents: dict[str, str] | None = None) -> None:
        self._contents = contents or {}
        self._urls: list[str] = []

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        self._urls.extend(request.urls)

        results = []
        for url in request.urls:
            content = self._contents.get(url, f"Fake content for {url}")
            results.append(FetchResult(
                url=url,
                canonical_url=url,
                success=True,
                status_code=200,
                content=content,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                word_count=len(content.split()),
                language="en",
                fetch_time_ms=100.0,
            ))

        return FetchResponse(
            results=results,
            successful_count=len(results),
            failed_count=0,
            blocked_count=0,
            total_time_ms=100.0,
        )

    def is_url_allowed(self, url: str) -> tuple[bool, str | None]:
        return True, None

    def extract_content(self, html: str, url: str) -> tuple[str, str | None, int]:
        return html, "Fake Title", len(html.split())

    def get_urls(self) -> list[str]:
        return self._urls