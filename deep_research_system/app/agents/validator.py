from __future__ import annotations

import logging

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    name = "validator"
    prompt_template_name = ""

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(required_capabilities=["extraction"], preferred_cost_tier="low")

    async def run(self, state: ResearchState) -> dict:
        report = state.final_report or {}
        issues = []

        if not report.get("title"):
            issues.append("Missing report title")
        if not report.get("executive_summary"):
            issues.append("Missing executive summary")
        if not report.get("sections"):
            issues.append("Missing report sections")

        for section in report.get("sections", []):
            if not section.get("citations"):
                issues.append(f"Section '{section.get('heading', '?')}' has no citations")

        return {"valid": len(issues) == 0, "issues": issues}
