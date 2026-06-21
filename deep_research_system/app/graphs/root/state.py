"""Root Graph State - top-level state for the entire research run.

Key constraints:
- JSON-safe
- No HTTP clients, DB connections, or exceptions
- Authoritative pointers for analysis, critique, report
- Budget tracking
- Loop counters with hard limits
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from app.graphs.shared.reducers import (
    append_list,
    max_int,
    merge_branch_results,
    merge_dict,
    merge_unique_strings,
    merge_usage,
    override,
)


class ResearchState(TypedDict, total=False):
    """Root state for the research graph.

    This state is checkpointed after each superstep.
    """

    # Identity
    run_id: str
    thread_id: str
    user_id: str | None
    query: str
    task_type: str
    requested_strategy: str
    selected_strategy: str | None

    # Run status
    status: Annotated[str, override]
    current_phase: str
    started_at: str
    deadline_at: str | None
    cancel_requested: bool

    # Config snapshot
    config_snapshot_id: str
    config_hash: str

    # Budget
    budget: dict
    usage: Annotated[dict, merge_usage]

    # Plan
    plan_artifact_id: str | None
    plan_summary: dict | None

    # Research loops
    research_round: Annotated[int, max_int]
    max_research_rounds: int
    pending_subtasks: list[dict]
    completed_subtask_ids: Annotated[list[str], merge_unique_strings]
    branch_result_refs: Annotated[dict[str, str], merge_branch_results]

    # Evidence and analysis
    evidence_ids: Annotated[list[str], merge_unique_strings]
    authoritative_analysis_id: Annotated[str | None, override]
    authoritative_critique_id: Annotated[str | None, override]

    # Debate
    debate_round: Annotated[int, max_int]
    position_result_refs: Annotated[dict[str, str], merge_branch_results]
    debate_round_refs: Annotated[list[str], merge_unique_strings]

    # Report
    authoritative_report_id: Annotated[str | None, override]
    validation_result_id: str | None
    repair_count: Annotated[int, max_int]
    max_repairs: int

    # Terminal
    warnings: Annotated[list[dict], append_list]
    errors: Annotated[list[dict], append_list]
    terminal_reason: str | None
