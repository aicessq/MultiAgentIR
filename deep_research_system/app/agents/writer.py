from __future__ import annotations

import json
import logging
from datetime import datetime
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
            model_slot="writing",
            required_capabilities=["writing", "synthesis"],
            preferred_cost_tier="high",
            complexity="hard",
        )

    def _build_prompt(self, state: ResearchState) -> str:
        template = state.writer_template or self.prompt_template_name
        return self.prompt_loader.render(template, **self._prompt_context(state))

    async def run(self, state: ResearchState, on_event=None) -> dict:
        result = await super().run(state, on_event=on_event)
        return self._enforce_source_registry(result, state)

    @staticmethod
    def _enforce_source_registry(result: dict, state: ResearchState) -> dict:
        registered = set(state.source_registry.keys())
        for section in result.get("sections", []):
            original = section.get("citations", [])
            filtered = [c for c in original if c in registered]
            if len(filtered) < len(original):
                removed = len(original) - len(filtered)
                logger.warning(f"Stripped {removed} unregistered citation(s) from section '{section.get('heading', '?')}'")
            section["citations"] = filtered
        return result

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        analysis = state.analyses[0] if state.analyses else {}
        critique = state.critiques[0] if state.critiques else {}
        claim_graph = state.claim_graph
        source_registry_list = [
            {"url": url, **src} for url, src in state.source_registry.items()
        ]

        # Build evidence catalog from all sub_results
        evidence_catalog = []
        for sq_id, result in state.sub_results.items():
            for ev in result.get("evidence", []):
                evidence_catalog.append(ev)

        base = {
            "research_goal": state.task.user_query,
            "as_of_date": datetime.now().strftime("%Y-%m-%d"),
            "analysis_content": json.dumps(analysis, ensure_ascii=False, indent=2),
            "critique_content": json.dumps(critique, ensure_ascii=False, indent=2),
            "claim_graph": json.dumps(claim_graph, ensure_ascii=False, indent=2),
            "source_registry": json.dumps(source_registry_list, ensure_ascii=False, indent=2),
            "evidence_catalog": json.dumps(evidence_catalog, ensure_ascii=False, indent=2),
            "repair_context": state.repair_context,
        }
        # Memo template needs debate-specific variables
        if "memo" in (state.writer_template or ""):
            debate = state.debate_results
            base.update({
                "pro_content": json.dumps(debate.get("pro", {}), ensure_ascii=False, indent=2),
                "con_content": json.dumps(debate.get("con", {}), ensure_ascii=False, indent=2),
                "neutral_content": json.dumps(debate.get("neutral", {}), ensure_ascii=False, indent=2),
                "synthesis_content": json.dumps(analysis, ensure_ascii=False, indent=2),
            })
        return base
