from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.schemas.state import ResearchState
from app.schemas.task import TaskRequirement

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
        # Pass 1: Code-level structural checks
        report = state.final_report or {}
        structural_issues = self._structural_check(report)

        # Pass 2: LLM-based evidence validation
        llm_result = await super().run(state, on_event=on_event)

        # Merge results
        all_issues = structural_issues + llm_result.get("issues", [])
        schema_valid = llm_result.get("schema_valid", True)
        structure_valid = len(structural_issues) == 0
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
            "warnings": llm_result.get("warnings", []),
        }

    @staticmethod
    def _compute_quality_score(report: dict, claim_graph: list, source_registry: dict) -> dict:
        scores: dict[str, float] = {}

        # Structural completeness (0-25)
        has_title = bool(report.get("title"))
        has_summary = bool(report.get("executive_summary"))
        has_sections = len(report.get("sections", [])) >= 3
        has_limitations = bool(report.get("limitations"))
        scores["structural"] = sum([has_title * 5, has_summary * 5, has_sections * 10, has_limitations * 5])

        # Citation coverage (0-25)
        sections = report.get("sections", [])
        total_citations = sum(len(s.get("citations", [])) for s in sections)
        sections_with_citations = sum(1 for s in sections if s.get("citations"))
        scores["citations"] = min(25.0, (sections_with_citations * 5) + min(10.0, total_citations))

        # Claim-evidence binding (0-25)
        claims_in_graph = len(claim_graph)
        claims_cited = sum(len(s.get("claim_ids", [])) for s in sections)
        scores["evidence_binding"] = min(25.0, (claims_cited / max(claims_in_graph, 1)) * 25)

        # Source quality (0-25)
        avg_credibility = 0.0
        if source_registry:
            avg_credibility = sum(
                s.get("credibility_score", 0.5) for s in source_registry.values()
            ) / len(source_registry)
        scores["source_quality"] = avg_credibility * 25

        scores["total"] = round(sum(scores.values()), 1)
        return scores

    @staticmethod
    def _structural_check(report: dict) -> list[dict]:
        issues = []
        if not report.get("title"):
            issues.append({"severity": "high", "location": "report", "problem": "缺少报告标题", "fix": "补充标题"})
        if not report.get("executive_summary"):
            issues.append({"severity": "high", "location": "report", "problem": "缺少执行摘要", "fix": "补充执行摘要"})
        sections = report.get("sections", [])
        if len(sections) < 3:
            issues.append({"severity": "medium", "location": "report", "problem": f"章节数不足（{len(sections)}个）", "fix": "至少需要3个章节"})
        for section in sections:
            heading = section.get("heading", "?")
            if not section.get("citations"):
                issues.append({"severity": "medium", "location": heading, "problem": f"章节'{heading}'缺少引用来源", "fix": "补充 citations"})
        if not report.get("limitations"):
            issues.append({"severity": "low", "location": "report", "problem": "缺少局限性说明", "fix": "补充 limitations"})
        return issues
