"""Hierarchical Graph State.

Extends Root State with hierarchical-specific fields.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from app.graphs.shared.reducers import append_list, max_int, merge_dict, merge_unique_strings, override


class HierarchicalState(TypedDict, total=False):
    """State for the hierarchical research graph.

    Flow:
    prepare_research -> dispatch_research_wave -> [research_branch x N] -> join_research -> build_analysis -> critique -> critique_router -> [write_report | generate_followups]
    """

    # From root state (inherited)
    run_id: str
    query: str
    task_type: str
    config_snapshot_id: str

    # Wave tracking
    current_wave: int
    max_waves: int
    wave_size: int

    # Subtasks
    pending_subtasks: list[dict]
    completed_subtask_ids: Annotated[list[str], merge_unique_strings]
    failed_subtask_ids: Annotated[list[str], merge_unique_strings]

    # Results from branches
    branch_results: Annotated[dict[str, dict], merge_dict]
    evidence_ids: Annotated[list[str], merge_unique_strings]

    # Analysis
    analysis_revision_id: Annotated[str | None, override]
    analysis_revisions: Annotated[list[str], merge_unique_strings]

    # Critique
    critique_revision_id: Annotated[str | None, override]
    critique_revisions: Annotated[list[str], merge_unique_strings]
    critique_findings: Annotated[list[dict], append_list]

    # Followup
    followup_queries: Annotated[list[str], merge_unique_strings]

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
