from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    name = "writer"
    prompt_template_name = "writer/industry_report.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["writing", "synthesis"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        analysis = state.analyses[0] if state.analyses else {}
        critique = state.critiques[0] if state.critiques else {}
        return {
            "research_goal": state.task.user_query,
            "analysis_content": json.dumps(analysis, ensure_ascii=False, indent=2),
            "critique_content": json.dumps(critique, ensure_ascii=False, indent=2),
        }
