"""Debate Graph Nodes.

Flow:
generate_hypotheses -> dispatch_debate_branches -> [debate_branch x N] -> join_debate -> cross_examine -> synthesize -> write_report -> validate_report -> validation_router -> [finalize_debate | repair_report -> validate_report | quality_gate_failed]

Key constraints:
- DebatePosition enum used for all position references
- Each branch produces evidence for one hypothesis from one position
- Cross-examination compares positions and identifies conflicts
- Synthesis resolves conflicts into unified claim graph
- Quality failure is terminal state
"""

from __future__ import annotations

import logging

from app.domain.enums import DebatePosition, QualityDecision, RunStatus
from app.graphs.debate.state import DebateState

logger = logging.getLogger(__name__)


async def generate_hypotheses_node(state: DebateState) -> dict:
    """Generate hypotheses from the query.

    Returns incremental update with hypotheses.
    """
    query = state["query"]

    # Generate hypotheses from the query
    hypotheses = [
        f"Hypothesis A: {query} is strongly supported",
        f"Hypothesis B: {query} is not supported",
        f"Hypothesis C: {query} requires nuance/alternative view",
    ]

    return {
        "hypotheses": hypotheses,
        "current_hypothesis_index": 0,
        "max_hypotheses": len(hypotheses),
        "status": "running",
    }


async def dispatch_debate_branches_node(state: DebateState) -> dict:
    """Dispatch debate branches for each hypothesis.

    Returns incremental update with branches to process.
    """
    hypotheses = state.get("hypotheses", [])
    current_index = state.get("current_hypothesis_index", 0)

    if current_index >= len(hypotheses):
        return {"status": "debate_complete"}

    # Create branches for current hypothesis with positions
    hypothesis = hypotheses[current_index]
    branches = {
        f"support-{current_index}": {
            "hypothesis": hypothesis,
            "position": DebatePosition.SUPPORT.value,
        },
        f"oppose-{current_index}": {
            "hypothesis": hypothesis,
            "position": DebatePosition.OPPOSE.value,
        },
    }

    # Alternative position for every other hypothesis
    if current_index % 2 == 0:
        branches[f"alternative-{current_index}"] = {
            "hypothesis": hypothesis,
            "position": DebatePosition.ALTERNATIVE.value,
        }

    return {
        "debate_positions": {bid: b["position"] for bid, b in branches.items()},
        "current_hypothesis_index": current_index + 1,
    }


async def join_debate_node(state: DebateState) -> dict:
    """Join debate branch results.

    Returns incremental update with merged evidence and results.
    """
    debate_results = state.get("debate_results", {})
    evidence_ids = state.get("evidence_ids", [])
    completed = state.get("completed_branch_ids", [])
    failed = state.get("failed_branch_ids", [])

    # Collect evidence from branches
    new_evidence = []
    for branch_id, result in debate_results.items():
        if branch_id not in completed and branch_id not in failed:
            completed.append(branch_id)
            new_evidence.extend(result.get("evidence_ids", []))

    return {
        "completed_branch_ids": completed,
        "evidence_ids": new_evidence,
        "status": "cross_examine_ready" if len(completed) > 0 else "partial",
    }


async def cross_examine_node(state: DebateState) -> dict:
    """Cross-examine debate results to identify conflicts.

    Returns incremental update with findings.
    """
    debate_results = state.get("debate_results", {})
    debate_positions = state.get("debate_positions", {})

    if not debate_results:
        return {
            "status": "failed",
            "errors": ["No debate results to cross-examine"],
            "terminal_reason": "insufficient_evidence",
        }

    # Identify conflicts between positions
    findings = []
    support_evidence = []
    oppose_evidence = []

    for branch_id, result in debate_results.items():
        position = debate_positions.get(branch_id, "")
        evidence = result.get("evidence_ids", [])
        if position == DebatePosition.SUPPORT.value:
            support_evidence.extend(evidence)
        elif position == DebatePosition.OPPOSE.value:
            oppose_evidence.extend(evidence)

    # Detect conflicts
    if support_evidence and oppose_evidence:
        findings.append({
            "type": "conflict",
            "description": "Support and oppose positions have conflicting evidence",
            "support_count": len(support_evidence),
            "oppose_count": len(oppose_evidence),
        })

    if not findings:
        findings.append({
            "type": "consensus",
            "description": "Positions largely agree or insufficient data for conflict",
        })

    import uuid
    revision_id = f"cross-examine-{uuid.uuid4().hex[:8]}"

    return {
        "cross_examine_findings": findings,
        "cross_examine_revision_id": revision_id,
        "status": "cross_examine_complete",
    }


async def synthesize_node(state: DebateState) -> dict:
    """Synthesize debate positions into unified analysis.

    Returns incremental update with synthesis and claim graph.
    """
    findings = state.get("cross_examine_findings", [])
    debate_results = state.get("debate_results", {})

    if not findings:
        return {
            "status": "failed",
            "errors": ["No cross-examine findings to synthesize"],
        }

    # Build claim graph from debate results
    claim_graph = []
    for branch_id, result in debate_results.items():
        position = state.get("debate_positions", {}).get(branch_id, "")
        claim_graph.append({
            "branch_id": branch_id,
            "position": position,
            "evidence_count": len(result.get("evidence_ids", [])),
            "status": result.get("status", "unknown"),
        })

    import uuid
    synthesis_id = f"synthesis-{uuid.uuid4().hex[:8]}"

    return {
        "synthesis_id": synthesis_id,
        "synthesis_revisions": [synthesis_id],
        "claim_graph": claim_graph,
        "status": "synthesis_complete",
    }


async def write_report_node(state: DebateState) -> dict:
    """Write report from synthesis.

    Returns incremental update with report revision.
    """
    synthesis_id = state.get("synthesis_id")

    if not synthesis_id:
        return {
            "status": "failed",
            "errors": ["No synthesis for report"],
        }

    import uuid
    report_id = f"report-{uuid.uuid4().hex[:8]}"

    return {
        "report_revision_id": report_id,
        "report_revisions": [report_id],
        "status": "report_complete",
    }


async def validate_report_node(state: DebateState) -> dict:
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
    score = 90.0
    decision = QualityDecision.PASS.value if score >= 85 else QualityDecision.REPAIR.value

    return {
        "validation_result": {"score": score, "decision": decision},
        "validation_decision": decision,
        "status": "validated",
    }


def validation_router(state: DebateState) -> str:
    """Route based on validation result.

    Returns next node name.
    """
    decision = state.get("validation_decision")
    repair_count = state.get("repair_count", 0)
    max_repairs = state.get("max_repairs", 2)

    if decision == QualityDecision.PASS.value:
        return "finalize_debate"
    elif decision == QualityDecision.REPAIR.value and repair_count < max_repairs:
        return "repair_report"
    else:
        return "quality_gate_failed"


async def repair_report_node(state: DebateState) -> dict:
    """Repair report based on validation feedback.

    Returns incremental update with repair instructions.
    """
    repair_count = state.get("repair_count", 0)

    return {
        "repair_count": repair_count + 1,
        "repair_instructions": [f"Repair attempt {repair_count + 1}"],
        "status": "repairing",
    }


async def quality_gate_failed_node(state: DebateState) -> dict:
    """Handle quality gate failure.

    Returns terminal state.
    """
    return {
        "status": RunStatus.FAILED_QUALITY_GATE.value,
        "terminal_reason": "quality_gate_failed",
        "errors": ["Report failed quality gate after maximum repairs"],
    }


async def finalize_debate_node(state: DebateState) -> dict:
    """Finalize debate research.

    Returns terminal state.
    """
    return {
        "status": RunStatus.COMPLETED.value,
        "terminal_reason": "success",
    }
