from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class DebateAgent(BaseAgent):
    name = "debate"
    prompt_template_name = "debate/hypothesis_agent.zh.j2"

    def __init__(self, hypothesis: str = "", branch: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.hypothesis = hypothesis
        self.branch = branch or "h_0"
        self.name = self.branch

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="reasoning",
            required_capabilities=["reasoning", "web_search_native"],
            preferred_cost_tier="mid",
            complexity="medium",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        return {
            "research_goal": state.task.user_query,
            "hypothesis": self.hypothesis,
        }

    def _parse_output(self, content: str) -> dict:
        result = super()._parse_output(content)
        result.setdefault("branch", self.branch)
        result.setdefault("hypothesis", self.hypothesis)
        return result


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"
    prompt_template_name = "debate/synthesizer_v2.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="writing",
            required_capabilities=["strong_reasoning", "synthesis"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        return {
            "research_goal": state.task.user_query,
            "hypothesis_results": state.debate_results,
        }
