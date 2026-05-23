from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class ReaderAgent(BaseAgent):
    name = "reader"
    prompt_template_name = "reader/v1_extraction.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            required_capabilities=["long_context", "extraction"],
            preferred_cost_tier="low",
            min_context_window=32000,
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        sq_id = list(state.sub_results.keys())[0] if state.sub_results else "sq_1"
        sq_data = state.sub_results.get(sq_id, {})
        sq_info = next((sq for sq in state.plan if sq.get("id") == sq_id), {})
        return {
            "sub_question": sq_info.get("question", ""),
            "sub_question_id": sq_id,
            "sources": sq_data.get("sources", []),
        }
