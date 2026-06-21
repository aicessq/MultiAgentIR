"""Research Branch State - lightweight, JSON-safe TypedDict.

Key constraints:
- Only JSON-safe types
- No HTTP clients, DB connections, or exceptions
- Incremental updates only
- Artifact IDs stored, not full artifacts
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from app.schemas.state import append_list, merge_dict, merge_unique_strings


class ResearchBranchState(TypedDict, total=False):
    """State for a single research branch (subtask).

    This state is passed to and returned from each node.
    Nodes only return incremental updates.
    """

    # Identity
    run_id: str
    subtask_id: str
    question: str
    research_round: int

    # Status
    status: str  # "pending", "in_progress", "completed", "partial", "failed"
    current_node: str
    started_at: str
    finished_at: str | None

    # Search
    queries: Annotated[list[str], append_list]
    search_result_set_id: str | None
    search_results_count: int

    # Documents
    document_ids: Annotated[list[str], merge_unique_strings]
    documents_fetched: int
    documents_failed: int

    # Evidence
    evidence_ids: Annotated[list[str], merge_unique_strings]
    evidence_count: int
    evidence_validated: int
    evidence_rejected: int

    # Results
    source_registry: Annotated[dict[str, dict], merge_dict]
    warnings: Annotated[list[str], append_list]
    errors: Annotated[list[str], append_list]

    # Budget
    tokens_used: int
    cost_usd: float
