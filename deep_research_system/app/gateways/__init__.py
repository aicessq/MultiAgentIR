"""Gateways module - external dependency interfaces.

Gateways provide clean interfaces to external systems:
- ModelGateway: LLM calls with structured output
- SearchGateway: Search queries (URLs/snippets only)
- DocumentFetcher: Full content download
- ArtifactStore: Artifact persistence

All gateways have Fake implementations for testing.
"""

from app.gateways.model import (
    DefaultModelGateway,
    FakeModelGateway,
    ModelGateway,
    ModelRequest,
    ModelResponse,
    ModelSpec,
)
from app.gateways.search import (
    DefaultSearchGateway,
    FakeSearchGateway,
    SearchGateway,
    SearchQuery,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultSet,
)
from app.gateways.fetch import (
    DefaultDocumentFetcher,
    DocumentFetcher,
    FakeDocumentFetcher,
    FetchRequest,
    FetchResponse,
    FetchResult,
)
from app.gateways.storage import (
    ArtifactStore,
    InMemoryArtifactStore,
    FileArtifactStore,
)

__all__ = [
    # Model
    "DefaultModelGateway",
    "FakeModelGateway",
    "ModelGateway",
    "ModelRequest",
    "ModelResponse",
    "ModelSpec",
    # Search
    "DefaultSearchGateway",
    "FakeSearchGateway",
    "SearchGateway",
    "SearchQuery",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "SearchResultSet",
    # Fetch
    "DefaultDocumentFetcher",
    "DocumentFetcher",
    "FakeDocumentFetcher",
    "FetchRequest",
    "FetchResponse",
    "FetchResult",
    # Storage
    "ArtifactStore",
    "InMemoryArtifactStore",
    "FileArtifactStore",
]