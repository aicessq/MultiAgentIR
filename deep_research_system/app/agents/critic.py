from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    name = "critic"
    prompt_template_name = "critic/v1_red_team.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["strong_reasoning", "critique"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        # In hierarchical topology, use analyzer output; in debate, use debate results
        if state.debate_results:
            content = state.debate_results
        elif state.analyses:
            content = state.analyses[0]
        else:
            content = {}
        return {
            "analysis_content": json.dumps(content, ensure_ascii=False, indent=2),
        }
