"""Debate Graph Builder.

Builds the debate research graph with:
- Hypothesis generation
- Parallel debate branches with positions (support/oppose/alternative)
- Cross-examination and conflict detection
- Synthesis into unified claim graph
- Report validation and repair
- Quality gate terminal states

Flow:
generate_hypotheses -> dispatch_debate_branches -> [debate_branch x N] -> join_debate -> cross_examine -> synthesize -> write_report -> validate_report -> validation_router -> [finalize_debate | repair_report -> validate_report | quality_gate_failed]
"""

from __future__ import annotations

from typing import Any

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


class DebateGraphBuilder:
    """Builder for debate research graph.

    Usage:
        builder = DebateGraphBuilder(
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
        """Build the debate graph structure.

        Returns a dict describing the graph.
        In Phase 5, this will return an actual compiled LangGraph.
        """
        return {
            "type": "debate",
            "nodes": {
                "generate_hypotheses": {
                    "func": generate_hypotheses_node,
                    "next": "dispatch_debate_branches",
                },
                "dispatch_debate_branches": {
                    "func": dispatch_debate_branches_node,
                    "next": "debate_branch",  # Fan-out to branches
                },
                "debate_branch": {
                    "func": None,  # External subgraph (simulated)
                    "next": "join_debate",
                },
                "join_debate": {
                    "func": join_debate_node,
                    "next": "cross_examine",
                },
                "cross_examine": {
                    "func": cross_examine_node,
                    "next": "synthesize",
                },
                "synthesize": {
                    "func": synthesize_node,
                    "next": "write_report",
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
                        "finalize_debate": "finalize_debate",
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
                "finalize_debate": {
                    "func": finalize_debate_node,
                    "next": None,  # Terminal
                },
            },
            "entry": "generate_hypotheses",
        }

    async def run(self, initial_state: DebateState) -> DebateState:
        """Run the debate graph.

        This is a simplified execution engine.
        In Phase 5, this will use LangGraph's streaming API.
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
                # External subgraph (debate_branch)
                # Simulate branch execution for each position
                state["debate_results"] = state.get("debate_results", {})
                for branch_id, position in state.get("debate_positions", {}).items():
                    if branch_id not in state["debate_results"]:
                        state["debate_results"][branch_id] = {
                            "evidence_ids": [f"evid-{branch_id}"],
                            "position": position,
                            "status": "completed",
                        }
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
                    override_keys = {
                        "status", "current_phase", "terminal_reason",
                        "cross_examine_revision_id", "synthesis_id", "report_revision_id",
                        "validation_decision", "current_hypothesis_index", "repair_count",
                    }
                    for key, value in update.items():
                        if key in override_keys:
                            state[key] = value
                        elif key in state and isinstance(state[key], list) and isinstance(value, list):
                            try:
                                state[key] = list(dict.fromkeys(state[key] + value))
                            except TypeError:
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
