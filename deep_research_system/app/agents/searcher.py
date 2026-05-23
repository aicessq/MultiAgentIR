from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from app.agents.base import BaseAgent
from app.prompts.renderer import get_prompt_loader
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
        self._planned_queries: list[dict] | None = None

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="search",
            required_capabilities=["web_search_native"],
            preferred_cost_tier="low",
            complexity="simple",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        sq = state.plan[0] if state.plan else {}
        # Use planned queries if available, otherwise fall back to original
        queries = sq.get("search_queries", [state.task.user_query])
        if self._planned_queries:
            queries = [p["query"] for p in self._planned_queries]
        return {
            "sub_question": sq.get("question", state.task.user_query),
            "sub_question_id": sq.get("id", "sq_1"),
            "search_queries": queries,
            "max_sources": state.task.max_sources,
            "search_results": self._cached_results,
        }

    async def _plan_queries(self, state: ResearchState, sq: dict, on_event: Callable | None = None) -> list[dict]:
        """Phase 1: Use LLM to optimize search queries based on hypothesis."""
        prompt_loader = get_prompt_loader()
        context = {
            "sub_question": sq.get("question", state.task.user_query),
            "hypothesis": sq.get("hypothesis", ""),
            "counter_evidence_needed": sq.get("counter_evidence_needed", []),
            "search_queries": sq.get("search_queries", [state.task.user_query]),
        }
        prompt = prompt_loader.render("searcher/v4_query_planner.zh.j2", **context)

        requirement = self.requirement(state)
        model = await self.router.select_model(requirement)
        if not model:
            return [{"query": q, "purpose": "", "preferred_source_types": []} for q in sq.get("search_queries", [])]

        api_key = self.key_pool.get_api_key(model.name) or ""
        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": "query_planner",
            "message": "正在优化搜索策略...",
        })

        content_parts: list[str] = []
        async for token in self.llm_client.stream(model, prompt, "", api_key):
            content_parts.append(token)

        full_content = "".join(content_parts)
        try:
            start = full_content.find("{")
            end = full_content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(full_content[start:end])
                return parsed.get("optimized_queries", [])
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: return original queries
        return [{"query": q, "purpose": "", "preferred_source_types": []} for q in sq.get("search_queries", [])]

    async def run(self, state: ResearchState, on_event: Callable | None = None) -> dict:
        sq = state.plan[0] if state.plan else {}

        # Phase 1: Query planning (LLM optimization)
        self._planned_queries = await self._plan_queries(state, sq, on_event)
        queries = [p["query"] for p in self._planned_queries] if self._planned_queries else sq.get("search_queries", [state.task.user_query])

        self._emit(on_event, {
            "type": "agent_thinking",
            "agent": self.name,
            "message": f"正在搜索 {len(queries)} 个查询...",
        })

        # Phase 2: Source collection (real search)
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

        # Phase 3: LLM synthesis of real results
        return await super().run(state, on_event=on_event)
