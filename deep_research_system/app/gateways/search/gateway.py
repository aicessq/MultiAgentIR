"""SearchGateway - unified interface for search operations.

Key responsibilities:
1. Execute search queries via multiple providers
2. Normalize results across providers
3. Deduplicate URLs
4. Filter low-quality sources
5. Rate limit per provider

Key constraints:
- SearchGateway ONLY returns URLs and snippets
- DocumentFetcher handles full content download
- NO evidence extraction here
- Provider failures should not crash the run
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.domain.enums import SourceTier
from app.domain.errors import SearchProviderError, TransientError
from app.gateways.search.spec import (
    SearchQuery,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultSet,
)

logger = logging.getLogger(__name__)


# Domain quality classification
HIGH_QUALITY_DOMAINS = [
    # Official sources
    "gov.cn", "gov.uk", "gov.au", "gov.us",
    # Regulatory
    "sec.gov", "fda.gov", "ema.europa.eu",
    # Financial data providers
    "bloomberg.com", "reuters.com", "wsj.com", "ft.com",
    # Industry research
    "mckinsey.com", "gartner.com", "idc.com", "forrester.com",
    # Academic
    "arxiv.org", "nature.com", "science.org", "springer.com",
]

MEDIUM_QUALITY_DOMAINS = [
    # News outlets
    "cnn.com", "bbc.com", "nytimes.com", "theguardian.com",
    # Tech news
    "techcrunch.com", "theverge.com", "wired.com",
    # Industry publications
    "forbes.com", "businessinsider.com", "economist.com",
]

LOW_QUALITY_DOMAINS = [
    # Social media
    "facebook.com", "twitter.com", "x.com", "linkedin.com",
    # Forums
    "zhihu.com", "reddit.com", "quora.com", "tieba.baidu.com",
    # Content farms
    "baijiahao.baidu.com", "toutiao.com",
]


class SearchGateway(ABC):
    """Abstract base class for search gateway."""

    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute search queries and return normalized results."""
        pass

    @abstractmethod
    def classify_domain(self, domain: str) -> SourceTier:
        """Classify domain quality tier."""
        pass

    @abstractmethod
    def deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate URLs from results."""
        pass


class DefaultSearchGateway(SearchGateway):
    """Default implementation of SearchGateway."""

    def __init__(
        self,
        providers: dict[str, dict] | None = None,
        max_concurrent_queries: int = 5,
        default_timeout: float = 30.0,
    ) -> None:
        self._providers = providers or {}
        self._max_concurrent_queries = max_concurrent_queries
        self._default_timeout = default_timeout
        self._rate_limiters: dict[str, asyncio.Semaphore] = {}

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute search queries and return normalized results.

        Process:
        1. Execute queries with concurrency limit
        2. Normalize results per provider
        3. Deduplicate URLs
        4. Filter low-quality sources
        5. Aggregate into response
        """
        start_time = time.time()

        # Execute queries concurrently with limit
        semaphore = asyncio.Semaphore(self._max_concurrent_queries)

        async def execute_query(query: SearchQuery) -> SearchResultSet:
            async with semaphore:
                return await self._execute_single_query(query, request)

        tasks = [execute_query(q) for q in request.queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        result_sets = []
        all_urls = set()
        errors = []
        providers_used = set()

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Query {i} failed: {result}")
                errors.append(f"Query {request.queries[i].query} failed: {str(result)}")
            else:
                result_sets.append(result)
                providers_used.add(result.provider)
                for r in result.results:
                    all_urls.add(r.url)

        # Deduplicate if requested
        if request.deduplicate_urls:
            for rs in result_sets:
                rs.results = self.deduplicate(rs.results)

        # Filter low-quality if requested
        if request.filter_low_quality:
            for rs in result_sets:
                rs.results = [r for r in rs.results if r.source_tier != SourceTier.TIER_3]

        total_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            result_sets=result_sets,
            total_results=sum(len(rs.results) for rs in result_sets),
            total_time_ms=total_time_ms,
            unique_urls=list(all_urls),
            errors=errors,
            provider_used=list(providers_used),
        )

    def classify_domain(self, domain: str) -> SourceTier:
        """Classify domain quality tier."""
        domain_lower = domain.lower()

        for hq_domain in HIGH_QUALITY_DOMAINS:
            if hq_domain in domain_lower:
                return SourceTier.TIER_1

        for mq_domain in MEDIUM_QUALITY_DOMAINS:
            if mq_domain in domain_lower:
                return SourceTier.TIER_2

        for lq_domain in LOW_QUALITY_DOMAINS:
            if lq_domain in domain_lower:
                return SourceTier.TIER_3

        return SourceTier.UNKNOWN

    def deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate URLs from results.

        Keeps the result with highest credibility_score for each URL.
        """
        url_to_result: dict[str, SearchResult] = {}

        for result in results:
            url_key = self._normalize_url(result.url)
            if url_key not in url_to_result:
                url_to_result[url_key] = result
            elif result.credibility_score > url_to_result[url_key].credibility_score:
                url_to_result[url_key] = result

        return list(url_to_result.values())

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        try:
            parsed = urlparse(url)
            # Remove scheme variations and trailing slashes
            normalized = parsed.netloc.lower() + parsed.path.rstrip("/")
            return hashlib.md5(normalized.encode()).hexdigest()
        except Exception:
            return url

    async def _execute_single_query(
        self, query: SearchQuery, request: SearchRequest
    ) -> SearchResultSet:
        """Execute a single query via available providers."""
        # Try providers in preference order
        providers_to_try = request.provider_preference or list(self._providers.keys())

        for provider_name in providers_to_try:
            if provider_name not in self._providers:
                continue

            try:
                return await self._call_provider(provider_name, query, request)
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue

        # No provider succeeded
        return SearchResultSet(
            set_id=f"failed_{hash(query.query)}",
            query_id=query.query,
            query=query.query,
            results=[],
            provider="none",
            errors=["No search provider available"],
        )

    async def _call_provider(
        self, provider_name: str, query: SearchQuery, request: SearchRequest
    ) -> SearchResultSet:
        """Call a specific search provider."""
        # Placeholder - actual implementation would call Tavily, Serper, etc.
        raise NotImplementedError("Subclasses must implement _call_provider")


class FakeSearchGateway(SearchGateway):
    """Fake gateway for testing."""

    def __init__(self, results: dict[str, list[SearchResult]] | None = None) -> None:
        self._results = results or {}
        self._queries: list[SearchQuery] = []

    async def search(self, request: SearchRequest) -> SearchResponse:
        self._queries.extend(request.queries)

        result_sets = []
        for query in request.queries:
            results = self._results.get(query.query, [
                SearchResult(
                    result_id=f"fake_{i}",
                    url=f"https://example.com/{query.query}/{i}",
                    title=f"Fake result {i} for {query.query}",
                    snippet=f"This is a fake snippet for {query.query}",
                    domain="example.com",
                    source_tier=SourceTier.TIER_2,
                    provider="fake",
                    position=i,
                )
                for i in range(query.max_results)
            ])
            result_sets.append(SearchResultSet(
                set_id=f"fake_{hash(query.query)}",
                query_id=query.query,
                query=query.query,
                results=results,
                provider="fake",
            ))

        return SearchResponse(
            result_sets=result_sets,
            total_results=sum(len(rs.results) for rs in result_sets),
            total_time_ms=100.0,
            unique_urls=[r.url for rs in result_sets for r in rs.results],
        )

    def classify_domain(self, domain: str) -> SourceTier:
        return SourceTier.TIER_2

    def deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        return results

    def get_queries(self) -> list[SearchQuery]:
        return self._queries