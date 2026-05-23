from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


class SearcherAgent(BaseAgent):
    name = "searcher"
    prompt_template_name = "searcher/v3_real_search.zh.j2"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._search_service = SearchService()
        self._cached_results: list[dict] = []

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["web_search_native"],
            preferred_cost_tier="low",
            complexity="simple",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        sq = state.plan[0] if state.plan else {}
        return {
            "sub_question": sq.get("question", state.task.user_query),
            "sub_question_id": sq.get("id", "sq_1"),
            "search_queries": sq.get("search_queries", [state.task.user_query]),
            "max_sources": state.task.max_sources,
            "search_results": self._cached_results,
        }

    async def run(self, state: ResearchState, on_event: Callable | None = None) -> dict:
        sq = state.plan[0] if state.plan else {}
        queries = sq.get("search_queries", [state.task.user_query])

        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": self.name,
            "message": f"正在搜索 {len(queries)} 个查询...",
        })

        # Execute real searches in parallel
        search_tasks = [
            self._search_service.search(q, max_results=state.task.max_sources)
            for q in queries
        ]
        results_per_query = await asyncio.gather(*search_tasks)

        # Flatten and deduplicate by URL
        seen_urls: set[str] = set()
        all_results: list[dict] = []
        for results in results_per_query:
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

        self._cached_results = all_results

        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": self.name,
            "message": f"搜索完成，获取到 {len(all_results)} 条结果，正在分析...",
        })

        # Now call LLM to synthesize the real results
        return await super().run(state, on_event=on_event)
