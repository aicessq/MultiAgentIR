"""Hierarchical Graph Nodes.

Flow:
prepare_research -> dispatch_research_wave -> [research_branch x N] -> join_research -> build_analysis -> critique -> critique_router -> [write_report | generate_followups -> dispatch_research_wave]

Key constraints:
- Writer only consumes authoritative_analysis_id
- Supplemental research goes through full evidence pipeline
- Quality failure is terminal state
- Loops have hard limits
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.domain.enums import QualityDecision, RunStatus
from app.graphs.hierarchical.state import HierarchicalState

logger = logging.getLogger(__name__)


async def prepare_research_node(state: HierarchicalState) -> dict:
    """Prepare research by initializing subtasks from plan.

    Returns incremental update with pending_subtasks.
    """
    query = state["query"]

    # Create subtasks from the query
    # In production, this would parse the plan artifact
    subtasks = [
        {"subtask_id": f"sub-{i}", "question": f"Aspect {i} of: {query}"}
        for i in range(3)
    ]

    return {
        "pending_subtasks": subtasks,
        "current_wave": 0,
        "max_waves": state.get("max_waves", 3),
        "wave_size": state.get("wave_size", 2),
        "status": "running",
    }


async def dispatch_research_wave_node(state: HierarchicalState) -> dict:
    """Dispatch next wave of research branches.

    Returns incremental update with subtasks to process.
    """
    pending = state.get("pending_subtasks", [])
    wave_size = state.get("wave_size", 2)
    current_wave = state.get("current_wave", 0)

    # Select next batch
    batch = pending[:wave_size]
    remaining = pending[wave_size:]

    if not batch:
        return {
            "status": "research_complete",
        }

    # Mark batch as dispatched (keep in state for branch execution)
    # The branch node will process these and clear them
    return {
        "pending_subtasks": batch,  # Keep batch for branch execution
        "current_wave": current_wave + 1,
    }


async def join_research_node(state: HierarchicalState) -> dict:
    """Join research wave results.

    Returns incremental update with merged evidence and branch results.
    """
    branch_results = state.get("branch_results", {})
    evidence_ids = state.get("evidence_ids", [])
    completed = state.get("completed_subtask_ids", [])

    # Collect evidence from branches
    new_evidence = []
    for subtask_id, result in branch_results.items():
        if subtask_id not in completed:
            completed.append(subtask_id)
            new_evidence.extend(result.get("evidence_ids", []))

    return {
        "completed_subtask_ids": completed,
        "evidence_ids": new_evidence,
        "status": "analysis_ready" if len(completed) > 0 else "partial",
    }


async def build_analysis_node(state: HierarchicalState) -> dict:
    """Build analysis from evidence.

    Returns incremental update with new analysis revision.
    """
    evidence_count = len(state.get("evidence_ids", []))

    if evidence_count == 0:
        return {
            "status": "failed",
            "errors": ["No evidence to build analysis"],
            "terminal_reason": "insufficient_evidence",
        }

    # Create new analysis revision
    import uuid
    revision_id = f"analysis-{uuid.uuid4().hex[:8]}"
    revision_number = len(state.get("analysis_revisions", [])) + 1

    return {
        "analysis_revision_id": revision_id,
        "analysis_revisions": [revision_id],
        "status": "analysis_complete",
    }


async def critique_node(state: HierarchicalState) -> dict:
    """Critique the analysis.

    Returns incremental update with critique findings.
    """
    analysis_id = state.get("analysis_revision_id")

    if not analysis_id:
        return {
            "status": "failed",
            "errors": ["No analysis to critique"],
        }

    # Simulate critique
    import uuid
    critique_id = f"critique-{uuid.uuid4().hex[:8]}"

    # Determine if more research is needed
    research_round = state.get("research_round", 0)
    max_rounds = state.get("max_research_rounds", 2)

    needs_more = research_round < max_rounds and len(state.get("evidence_ids", [])) < 5

    return {
        "critique_revision_id": critique_id,
        "critique_revisions": [critique_id],
        "critique_findings": [{"needs_more_research": needs_more}],
        "status": "critique_complete",
    }


def critique_router(state: HierarchicalState) -> str:
    """Route based on critique findings.

    Returns next node name.
    """
    findings = state.get("critique_findings", [])
    research_round = state.get("research_round", 0)
    max_rounds = state.get("max_research_rounds", 2)

    needs_more = any(f.get("needs_more_research") for f in findings)

    if needs_more and research_round < max_rounds:
        return "generate_followups"
    else:
        return "write_report"


async def generate_followups_node(state: HierarchicalState) -> dict:
    """Generate followup queries for supplemental research.

    Returns incremental update with followup queries.
    """
    research_round = state.get("research_round", 0)

    # Generate followup queries
    followups = [
        f"Followup query {i} for round {research_round + 1}"
        for i in range(2)
    ]

    # Create subtasks from followups
    subtasks = [
        {"subtask_id": f"followup-{research_round}-{i}", "question": q}
        for i, q in enumerate(followups)
    ]

    return {
        "followup_queries": followups,
        "pending_subtasks": subtasks,
        "research_round": research_round + 1,
        "status": "followup_ready",
    }


async def write_report_node(state: HierarchicalState) -> dict:
    """Write report from authoritative analysis.

    Returns incremental update with report revision.
    """
    analysis_id = state.get("analysis_revision_id")

    if not analysis_id:
        return {
            "status": "failed",
            "errors": ["No authoritative analysis for report"],
        }

    import uuid
    report_id = f"report-{uuid.uuid4().hex[:8]}"

    return {
        "report_revision_id": report_id,
        "report_revisions": [report_id],
        "status": "report_complete",
    }


async def validate_report_node(state: HierarchicalState) -> dict:
    """Validate report quality.

    Returns incremental update with validation result.
    """
    report_id = state.get("report_revision_id")

    if not report_id:
        return {
            "status": "failed",
            "errors": ["No report to validate"],
        }

    # Simulate validation
    score = 90.0  # Would be computed from actual validation
    decision = QualityDecision.PASS.value if score >= 85 else QualityDecision.REPAIR.value

    return {
        "validation_result": {"score": score, "decision": decision},
        "validation_decision": decision,
        "status": "validated",
    }


def validation_router(state: HierarchicalState) -> str:
    """Route based on validation result.

    Returns next node name.
    """
    decision = state.get("validation_decision")
    repair_count = state.get("repair_count", 0)
    max_repairs = state.get("max_repairs", 2)

    if decision == QualityDecision.PASS.value:
        return "finalize_hierarchical"
    elif decision == QualityDecision.REPAIR.value and repair_count < max_repairs:
        return "repair_report"
    else:
        return "quality_gate_failed"


async def repair_report_node(state: HierarchicalState) -> dict:
    """Repair report based on validation feedback.

    Returns incremental update with repair instructions.
    """
    repair_count = state.get("repair_count", 0)

    return {
        "repair_count": repair_count + 1,
        "repair_instructions": [f"Repair attempt {repair_count + 1}"],
        "status": "repairing",
    }


async def quality_gate_failed_node(state: HierarchicalState) -> dict:
    """Handle quality gate failure.

    Returns terminal state.
    """
    return {
        "status": RunStatus.FAILED_QUALITY_GATE.value,
        "terminal_reason": "quality_gate_failed",
        "errors": ["Report failed quality gate after maximum repairs"],
    }


async def finalize_hierarchical_node(state: HierarchicalState) -> dict:
    """Finalize hierarchical research.

    Returns terminal state.
    """
    return {
        "status": RunStatus.COMPLETED.value,
        "terminal_reason": "success",
    }
