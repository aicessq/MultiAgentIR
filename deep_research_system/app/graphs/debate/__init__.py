"""Debate Research Graph.

Top-level graph for debate research strategy:
1. Generate hypotheses from query
2. Dispatch parallel debate branches (support/oppose/alternative)
3. Cross-examine and critique
4. Synthesize positions into unified analysis
5. Write and validate report
6. Repair or finalize

Usage:
    from app.graphs.debate import DebateGraphBuilder

    builder = DebateGraphBuilder(
        model_gateway=model_gateway,
        search_gateway=search_gateway,
        document_fetcher=document_fetcher,
        artifact_store=artifact_store,
    )
    result = await builder.run(initial_state)
"""

from app.graphs.debate.state import DebateState
from app.graphs.debate.nodes import (
    generate_hypotheses_node,
    dispatch_debate_branches_node,
    join_debate_node,
    cross_examine_node,
    synthesize_node,
    write_report_node,
    validate_report_node,
    validation_router,
    repair_report_node,
    quality_gate_failed_node,
    finalize_debate_node,
)
from app.graphs.debate.builder import DebateGraphBuilder

__all__ = [
    "DebateState",
    "generate_hypotheses_node",
    "dispatch_debate_branches_node",
    "join_debate_node",
    "cross_examine_node",
    "synthesize_node",
    "write_report_node",
    "validate_report_node",
    "validation_router",
    "repair_report_node",
    "quality_gate_failed_node",
    "finalize_debate_node",
    "DebateGraphBuilder",
]
