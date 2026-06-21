"""Hierarchical Graph Builder.

Builds the hierarchical research graph with:
- Wave-based parallel research branches
- Analysis/critique revision cycle
- Supplemental research loop
- Report validation and repair
- Quality gate terminal states

Flow:
prepare_research -> dispatch_research_wave -> [research_branch x N] -> join_research -> build_analysis -> critique -> critique_router -> [write_report | generate_followups -> dispatch_research_wave]
write_report -> validate_report -> validation_router -> [finalize_hierarchical | repair_report -> validate_report | quality_gate_failed]
"""

from __future__ import annotations

from typing import Any

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


class HierarchicalGraphBuilder:
    """Builder for hierarchical research graph.

    Usage:
        builder = HierarchicalGraphBuilder(
            model_gateway=model_gateway,
            search_gateway=search_gateway,
            document_fetcher=document_fetcher,
            artifact_store=artifact_store,
        )
        graph = builder.build()
        result = await builder.run(initial_state)
    """

    def __init__(
        self,
        model_gateway: Any,
        search_gateway: Any,
        document_fetcher: Any,
        artifact_store: Any,
    ) -> None:
        self._model_gateway = model_gateway
        self._search_gateway = search_gateway
        self._document_fetcher = document_fetcher
        self._artifact_store = artifact_store

    def build(self) -> dict:
        """Build the hierarchical graph structure.

        Returns a dict describing the graph.
        In Phase 4, this will return an actual compiled LangGraph.
        """
        return {
            "type": "hierarchical",
            "nodes": {
                "prepare_research": {
                    "func": prepare_research_node,
                    "next": "dispatch_research_wave",
                },
                "dispatch_research_wave": {
                    "func": dispatch_research_wave_node,
                    "next": "research_branch",  # Fan-out to branches
                },
                "research_branch": {
                    "func": None,  # External subgraph
                    "next": "join_research",
                },
                "join_research": {
                    "func": join_research_node,
                    "next": "build_analysis",
                },
                "build_analysis": {
                    "func": build_analysis_node,
                    "next": "critique",
                },
                "critique": {
                    "func": critique_node,
                    "next": "critique_router",
                },
                "critique_router": {
                    "func": critique_router,
                    "branches": {
                        "generate_followups": "generate_followups",
                        "write_report": "write_report",
                    },
                },
                "generate_followups": {
                    "func": generate_followups_node,
                    "next": "dispatch_research_wave",  # Loop back
                },
                "write_report": {
                    "func": write_report_node,
                    "next": "validate_report",
                },
                "validate_report": {
                    "func": validate_report_node,
                    "next": "validation_router",
                },
                "validation_router": {
                    "func": validation_router,
                    "branches": {
                        "finalize_hierarchical": "finalize_hierarchical",
                        "repair_report": "repair_report",
                        "quality_gate_failed": "quality_gate_failed",
                    },
                },
                "repair_report": {
                    "func": repair_report_node,
                    "next": "write_report",  # Loop back
                },
                "quality_gate_failed": {
                    "func": quality_gate_failed_node,
                    "next": None,  # Terminal
                },
                "finalize_hierarchical": {
                    "func": finalize_hierarchical_node,
                    "next": None,  # Terminal
                },
            },
            "entry": "prepare_research",
        }

    async def run(self, initial_state: HierarchicalState) -> HierarchicalState:
        """Run the hierarchical graph.

        This is a simplified execution engine.
        In Phase 4, this will use LangGraph's streaming API.
        """
        graph = self.build()
        state = dict(initial_state)
        current = graph["entry"]
        max_steps = 50  # Safety limit
        steps = 0

        while current and steps < max_steps:
            steps += 1
            node = graph["nodes"][current]

            # Execute node
            if node["func"] is None:
                # External subgraph (research_branch)
                # Simulate branch execution
                state["branch_results"] = state.get("branch_results", {})
                for subtask in state.get("pending_subtasks", []):
                    state["branch_results"][subtask["subtask_id"]] = {
                        "evidence_ids": [f"evid-{subtask['subtask_id']}"],
                        "status": "completed",
                    }
                state["pending_subtasks"] = []
                current = node["next"]
                continue

            try:
                if current.endswith("_router"):
                    # Router node returns next node name
                    current = node["func"](state)
                else:
                    # Regular node returns state update
                    update = await node["func"](state)

                    # Merge update into state
                    # Keys that should be overridden (not merged)
                    override_keys = {
                        "status", "current_phase", "terminal_reason",
                        "analysis_revision_id", "critique_revision_id", "report_revision_id",
                        "validation_decision", "research_round", "repair_count",
                        "current_wave", "pending_subtasks",
                    }
                    for key, value in update.items():
                        if key in override_keys:
                            # Override: take new value
                            state[key] = value
                        elif key in state and isinstance(state[key], list) and isinstance(value, list):
                            # Deduplicate lists - only for hashable items
                            try:
                                state[key] = list(dict.fromkeys(state[key] + value))
                            except TypeError:
                                # Items are not hashable (e.g., dicts), append without dedup
                                state[key] = state[key] + value
                        elif key in state and isinstance(state[key], dict) and isinstance(value, dict):
                            state[key] = {**state[key], **value}
                        else:
                            state[key] = value

                    # Check terminal status
                    if state.get("status") in ("completed", "failed", "failed_quality_gate"):
                        break

                    current = node.get("next")
            except Exception as e:
                state["status"] = "failed"
                state["errors"] = state.get("errors", []) + [f"{current}: {str(e)}"]
                break

        return state
