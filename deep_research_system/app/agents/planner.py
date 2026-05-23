from __future__ import annotations

import json
import logging
from typing import Any

from typing import Callable

from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    name = "planner"
    prompt_template_name = "planner/v2_structured.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["strong_reasoning"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        from app.core.config import get_config
        topo_cfg = get_config().topology.get("hierarchical", {})
        return {
            "user_query": state.task.user_query,
            "task_type": state.task.task_type,
            "depth": state.task.depth,
            "max_sub_questions": topo_cfg.get("max_sub_questions", 6),
        }

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=10), reraise=True)
    async def run(self, state: ResearchState, on_event: Callable | None = None) -> dict:
        result = await super().run(state, on_event=on_event)
        if "sub_questions" not in result:
            logger.warning("Planner output missing sub_questions, retrying")
            raise ValueError("Invalid planner output")
        return result
