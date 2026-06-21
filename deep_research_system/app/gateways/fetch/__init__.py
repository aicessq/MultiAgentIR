"""Document fetcher module."""

from app.gateways.fetch.gateway import DefaultDocumentFetcher, DocumentFetcher, FakeDocumentFetcher
from app.gateways.fetch.spec import FetchRequest, FetchResponse, FetchResult

__all__ = [
    "DefaultDocumentFetcher",
    "DocumentFetcher",
    "FakeDocumentFetcher",
    "FetchRequest",
    "FetchResponse",
    "FetchResult",
]