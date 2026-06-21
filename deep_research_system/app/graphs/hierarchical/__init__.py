"""Hierarchical Research Graph.

Top-level graph for hierarchical research strategy:
1. Prepare research subtasks
2. Dispatch waves of parallel research branches
3. Join results and build analysis
4. Critique and decide on supplemental research
5. Write and validate report
6. Repair or finalize

Usage:
    from app.graphs.hierarchical import HierarchicalGraphBuilder
    
    builder = HierarchicalGraphBuilder(
        model_gateway=model_gateway,
        search_gateway=search_gateway,
        document_fetcher=document_fetcher,
        artifact_store=artifact_store,
    )
    result = await builder.run(initial_state)
"""

from app.graphs.hierarchical.state import HierarchicalState
from app.graphs.hierarchical.nodes import (
    prepare_research_node,
    dispatch_research_wave_node,
    join_research_node,
    build_analysis_node,
    critique_node,
    critique_router,
    generate_followups_node,
    write_report_node,
    validate_report_node,
    validation_router,
    repair_report_node,
    quality_gate_failed_node,
    finalize_hierarchical_node,
)
from app.graphs.hierarchical.builder import HierarchicalGraphBuilder

__all__ = [
    "HierarchicalState",
    "prepare_research_node",
    "dispatch_research_wave_node",
    "join_research_node",
    "build_analysis_node",
    "critique_node",
    "critique_router",
    "generate_followups_node",
    "write_report_node",
    "validate_report_node",
    "validation_router",
    "repair_report_node",
    "quality_gate_failed_node",
    "finalize_hierarchical_node",
    "HierarchicalGraphBuilder",
]