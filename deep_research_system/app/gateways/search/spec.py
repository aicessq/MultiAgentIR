"""Search request specification for the SearchGateway.

Key distinction from DocumentFetcher:
- SearchGateway: Returns URLs, titles, snippets, and metadata
- DocumentFetcher: Downloads and extracts full content

SearchGateway does NOT download documents.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import SourceTier


class SearchQuery(BaseModel):
    """A search query specification."""

    query: str
    purpose: str = "general"  # e.g., "market_data", "company_info"
    max_results: int = 10
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    source_requirements: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    prefer_domains: list[str] = Field(default_factory=list)
    language: str = "zh-CN"


class SearchResult(BaseModel):
    """A single search result (not a full document)."""

    result_id: str
    url: str
    title: str | None = None
    snippet: str | None = None
    source_type: str = "unknown"
    publish_date: datetime | None = None
    credibility_score: float = 0.5
    domain: str | None = None
    source_tier: SourceTier = SourceTier.UNKNOWN
    reliability: str = "medium"
    provider: str = "unknown"
    position: int = 0  # Position in search results
    metadata: dict = Field(default_factory=dict)


class SearchResultSet(BaseModel):
    """A set of search results for a query."""

    set_id: str
    query_id: str
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total_results: int = 0
    provider: str = "unknown"
    search_time_ms: float = 0.0
    has_more: bool = False
    next_page_token: str | None = None
    errors: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """Request for the SearchGateway."""

    queries: list[SearchQuery] = Field(default_factory=list)
    max_total_results: int = 50
    max_results_per_query: int = 10
    timeout_seconds: float = 30.0
    deduplicate_urls: bool = True
    filter_low_quality: bool = True
    provider_preference: list[str] = Field(default_factory=list)  # e.g., ["tavily", "serper"]


class SearchResponse(BaseModel):
    """Response from the SearchGateway."""

    result_sets: list[SearchResultSet] = Field(default_factory=list)
    total_results: int = 0
    total_time_ms: float = 0.0
    unique_urls: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    provider_used: list[str] = Field(default_factory=list)