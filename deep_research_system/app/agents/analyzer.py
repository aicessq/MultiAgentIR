from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    name = "analyzer"
    prompt_template_name = "analyzer/v1_cross_source.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
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
