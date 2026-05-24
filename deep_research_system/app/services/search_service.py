from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)
        self._last_mode: str = "mock"

    @property
    def last_mode(self) -> str:
        """Return 'real' if last search used Tavily API, 'mock' if simulated."""
        return self._last_mode

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        api_key = os.getenv("TAVILY_API_KEY", "")
        if api_key:
            results = await self._tavily_search(query, max_results, api_key)
            return results
        self._last_mode = "mock"
        return self._mock_search(query, max_results)

    async def _tavily_search(self, query: str, max_results: int, api_key: str) -> list[dict]:
        try:
            resp = await self._client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:500],
                    "source_type": "unknown",
                    "publish_date": r.get("published_date"),
                    "credibility_score": 0.6,
                })
            self._last_mode = "real"
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return self._mock_search(query, max_results)

    def _mock_search(self, query: str, max_results: int) -> list[dict]:
        return [
            {
                "title": f"Search result {i+1} for: {query}",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a mock search result for the query '{query}'. In production, this would contain real search results from Tavily or a native search model.",
                "source_type": "unknown",
                "publish_date": None,
                "credibility_score": 0.5,
            }
            for i in range(min(max_results, 3))
        ]

    async def close(self) -> None:
        await self._client.aclose()
