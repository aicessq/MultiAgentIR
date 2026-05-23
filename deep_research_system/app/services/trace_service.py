from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas.state import ResearchState

logger = logging.getLogger(__name__)


class TraceService:
    def __init__(self) -> None:
        self._traces: dict[str, list[dict]] = {}

    def record(self, task_id: str, state: ResearchState) -> None:
        self._traces[task_id] = state.audit_trail
        logger.info(f"Trace recorded for {task_id}: {len(state.audit_trail)} entries")

    def get_trace(self, task_id: str) -> list[dict]:
        return self._traces.get(task_id, [])

    def get_cost_summary(self, task_id: str) -> dict:
        trace = self.get_trace(task_id)
        cost_by_model: dict[str, float] = {}
        cost_by_agent: dict[str, float] = {}
        for entry in trace:
            model = entry.get("model", "unknown")
            agent = entry.get("agent", "unknown")
            cost = entry.get("cost", 0)
            cost_by_model[model] = cost_by_model.get(model, 0) + cost
            cost_by_agent[agent] = cost_by_agent.get(agent, 0) + cost
        return {
            "total_cost": sum(cost_by_model.values()),
            "by_model": cost_by_model,
            "by_agent": cost_by_agent,
            "total_calls": len(trace),
        }
