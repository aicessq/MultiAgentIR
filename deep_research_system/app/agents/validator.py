from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement
from app.validators.report_validator import validate_report

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    name = "validator"
    prompt_template_name = "validator/v2_evidence_check.zh.j2"

    def requirement(self, state: ResearchState) -> TaskRequirement:
        return TaskRequirement(
            model_slot="analysis",
            required_capabilities=["extraction"],
            preferred_cost_tier="low",
        )

    def _prompt_context(self, state: ResearchState) -> dict[str, Any]:
        report = state.final_report or {}
        # Build evidence catalog from sub_results
        evidence_catalog = []
        for sq_id, result in state.sub_results.items():
            for ev in result.get("evidence", []):
                evidence_catalog.append(ev)

        return {
            "report_content": json.dumps(report, ensure_ascii=False, indent=2),
            "claim_graph": json.dumps(state.claim_graph, ensure_ascii=False, indent=2),
            "source_urls": json.dumps(list(state.source_registry.keys()), ensure_ascii=False),
            "evidence_catalog": json.dumps(evidence_catalog, ensure_ascii=False, indent=2),
        }

    async def run(self, state: ResearchState, on_event=None) -> dict:
        report = state.final_report or {}

        self._emit(on_event, {"type": "agent_thinking", "agent": self.name, "message": "正在运行确定性校验..."})

        # Pass 1: Deterministic validation (always runs, fast)
        det_result = validate_report(report, state.claim_graph, state.source_registry)
        det_issues = det_result.get("issues", [])
        det_warnings = det_result.get("warnings", [])

        # If deterministic check finds high-severity issues, skip LLM and return failure
        has_high_det = any(i["severity"] == "high" for i in det_issues)
        if has_high_det:
            quality_scores = self._compute_quality_score(report, state.claim_graph, state.source_registry)
            result = {
                "valid": False,
                "score": quality_scores["total"],
                "quality_scores": quality_scores,
                "schema_valid": False,
                "structure_valid": False,
                "evidence_valid": False,
                "issues": det_issues,
                "warnings": det_warnings,
            }
            self._emit(on_event, {"type": "agent_output", "agent": self.name, "message": f"确定性校验未通过：{len(det_issues)} 个问题", "output": result})
            return result

        # Pass 2: LLM-based evidence validation
        self._emit(on_event, {"type": "agent_thinking", "agent": self.name, "message": "确定性校验通过，正在运行 LLM 证据校验..."})
        llm_result = await super().run(state, on_event=on_event)

        # Merge results — deterministic issues always included
        all_issues = det_issues + llm_result.get("issues", [])
        all_warnings = det_warnings + llm_result.get("warnings", [])
        schema_valid = llm_result.get("schema_valid", True)
        structure_valid = len(det_issues) == 0
        evidence_valid = llm_result.get("evidence_valid", True)

        # Compute quality score (independent of LLM score)
        quality_scores = self._compute_quality_score(report, state.claim_graph, state.source_registry)

        return {
            "valid": schema_valid and structure_valid and evidence_valid,
            "score": llm_result.get("score", quality_scores["total"]),
            "quality_scores": quality_scores,
            "schema_valid": schema_valid,
            "structure_valid": structure_valid,
            "evidence_valid": evidence_valid,
            "issues": all_issues,
            "warnings": all_warnings,
        }

    @staticmethod
    def _compute_quality_score(report: dict, claim_graph: list, source_registry: dict) -> dict:
        scores: dict[str, float] = {}

        # Structural completeness (0-25)
        has_title = bool(report.get("title"))
        raw_summary = report.get("executive_summary", "")
        has_summary = bool(raw_summary.get("content") if isinstance(raw_summary, dict) else raw_summary)
        has_sections = len(report.get("sections", [])) >= 3
        has_as_of_date = bool(report.get("as_of_date"))
        scores["structural"] = sum([has_title * 5, has_summary * 5, has_sections * 10, has_as_of_date * 5])

        # Citation coverage (0-25)
        sections = report.get("sections", [])
        total_citations = sum(len(s.get("citations", [])) for s in sections)
        sections_with_citations = sum(1 for s in sections if s.get("citations"))
        scores["citations"] = min(25.0, (sections_with_citations * 5) + min(10.0, total_citations))

        # Claim-evidence binding (0-25)
        claims_in_graph = len(claim_graph)
        claims_cited = sum(len(s.get("claim_ids", [])) for s in sections)
        key_claims_count = sum(len(s.get("key_claims", [])) for s in sections)
        binding_ratio = (claims_cited + key_claims_count) / max(claims_in_graph * 2, 1)
        scores["evidence_binding"] = min(25.0, binding_ratio * 25)

        # Risk register completeness (0-25)
        risk_register = report.get("risk_register", [])
        risk_score = 0.0
        if len(risk_register) >= 3:
            risk_score += 10.0
        if len(risk_register) >= 5:
            risk_score += 5.0
        # Check each risk has required fields
        complete_risks = sum(
            1 for r in risk_register
            if r.get("risk") and r.get("mechanism") and r.get("evidence_claim_ids")
        )
        risk_score += min(10.0, (complete_risks / max(len(risk_register), 1)) * 10)
        scores["risk_register"] = risk_score

        scores["total"] = round(sum(scores.values()), 1)
        return scores
