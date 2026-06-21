"""Debate Graph State.

Extends Root State with debate-specific fields.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from app.graphs.shared.reducers import append_list, max_int, merge_dict, merge_unique_strings, override


class DebateState(TypedDict, total=False):
    """State for the debate research graph.

    Flow:
    generate_hypotheses -> dispatch_debate_branches -> [debate_branch x N] -> join_debate -> cross_examine -> synthesize -> write_report -> validate_report -> validation_router -> [finalize_debate | repair_report -> validate_report | quality_gate_failed]
    """

    # From root state (inherited)
    run_id: str
    query: str
    task_type: str
    config_snapshot_id: str

    # Hypotheses
    hypotheses: Annotated[list[str], merge_unique_strings]
    current_hypothesis_index: int
    max_hypotheses: int

    # Debate branches
    debate_positions: Annotated[dict[str, str], merge_dict]  # branch_id -> position (support/oppose/alternative)
    debate_results: Annotated[dict[str, dict], merge_dict]   # branch_id -> result
    completed_branch_ids: Annotated[list[str], merge_unique_strings]
    failed_branch_ids: Annotated[list[str], merge_unique_strings]

    # Evidence
    evidence_ids: Annotated[list[str], merge_unique_strings]

    # Cross-examination
    cross_examine_findings: Annotated[list[dict], append_list]
    cross_examine_revision_id: Annotated[str | None, override]

    # Synthesis
    synthesis_id: Annotated[str | None, override]
    synthesis_revisions: Annotated[list[str], merge_unique_strings]
    claim_graph: Annotated[list[dict], append_list]

    # Report
    report_revision_id: Annotated[str | None, override]
    report_revisions: Annotated[list[str], merge_unique_strings]

    # Validation
    validation_result: dict | None
    validation_decision: str | None

    # Repair
    repair_instructions: Annotated[list[str], append_list]
    repair_count: Annotated[int, max_int]
    max_repairs: int

    # Terminal
    status: Annotated[str, override]
    terminal_reason: str | None
    warnings: Annotated[list[str], append_list]
    errors: Annotated[list[str], append_list]
