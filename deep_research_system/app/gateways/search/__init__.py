"""Search gateway module."""

from app.gateways.search.gateway import DefaultSearchGateway, FakeSearchGateway, SearchGateway
from app.gateways.search.spec import SearchQuery, SearchRequest, SearchResponse, SearchResult, SearchResultSet

__all__ = [
    "DefaultSearchGateway",
    "FakeSearchGateway",
    "SearchGateway",
    "SearchQuery",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "SearchResultSet",
]