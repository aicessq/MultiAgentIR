from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    name = "analyzer"
    prompt_template_name = "analyzer/v2_claim_graph.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="analysis",
            required_capabilities=["long_context", "reasoning"],
            preferred_cost_tier="mid",
            complexity="medium",
            min_context_window=32000,
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        return {
            "research_goal": state.task.user_query,
            "sub_results": state.sub_results,
        }

    def _summarize_output(self, parsed: dict) -> str:
        claims = parsed.get("claims", [])
        if not claims:
            return "分析完成: 0 claims"
        type_counts: dict[str, int] = {}
        for c in claims:
            ct = c.get("claim_type", "unknown")
            type_counts[ct] = type_counts.get(ct, 0) + 1
        parts = [f"{v}x {k}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1])]
        return f"分析完成: {len(claims)} claims ({', '.join(parts)})"
