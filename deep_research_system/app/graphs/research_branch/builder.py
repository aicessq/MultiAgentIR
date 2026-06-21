"""Research Branch Graph Builder.

Builds a StateGraph for a single research branch (subtask).

Flow:
plan_queries -> execute_search -> fetch_documents -> extract_evidence -> verify_evidence -> persist_branch_result

Key constraints:
- Each node returns incremental updates
- State is JSON-safe
- No in-place modifications
- Idempotent nodes
"""

from __future__ import annotations

from typing import Any

from app.graphs.research_branch.state import ResearchBranchState
from app.graphs.research_branch.nodes import (
    plan_queries_node,
    execute_search_node,
    fetch_documents_node,
    extract_evidence_node,
    verify_evidence_node,
    persist_branch_result_node,
)


class ResearchBranchBuilder:
    """Builder for research branch graph.

    Usage:
        builder = ResearchBranchBuilder(
            model_gateway=model_gateway,
            search_gateway=search_gateway,
            document_fetcher=document_fetcher,
            artifact_store=artifact_store,
        )
        graph = builder.build()
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
        """Build the research branch graph.

        Returns a dict describing the graph structure.
        In Phase 3, this will return an actual compiled LangGraph.
        """
        # For now, return a sequential pipeline description
        # In Phase 3, this will use StateGraph from langgraph
        return {
            "type": "sequential",
            "nodes": [
                {
                    "name": "plan_queries",
                    "func": self._wrap_node(plan_queries_node, self._model_gateway),
                    "description": "Generate search queries for the subtask",
                },
                {
                    "name": "execute_search",
                    "func": self._wrap_node(execute_search_node, self._search_gateway),
                    "description": "Execute search queries",
                },
                {
                    "name": "fetch_documents",
                    "func": self._wrap_node(fetch_documents_node, self._document_fetcher),
                    "description": "Fetch full content from URLs",
                },
                {
                    "name": "extract_evidence",
                    "func": self._wrap_node(extract_evidence_node, self._model_gateway),
                    "description": "Extract evidence from documents",
                },
                {
                    "name": "verify_evidence",
                    "func": self._wrap_node(verify_evidence_node),
                    "description": "Verify evidence quality",
                },
                {
                    "name": "persist_branch_result",
                    "func": self._wrap_node(persist_branch_result_node, self._artifact_store),
                    "description": "Persist final branch result",
                },
            ],
        }

    def _wrap_node(self, node_func, *args):
        """Wrap a node function with its dependencies."""
        async def wrapper(state: ResearchBranchState) -> dict:
            return await node_func(state, *args)
        return wrapper

    async def run(self, initial_state: ResearchBranchState) -> ResearchBranchState:
        """Run the research branch pipeline.

        This is a simplified sequential execution.
        In Phase 3, this will use LangGraph's streaming API.
        """
        graph = self.build()
        state = dict(initial_state)

        for node in graph["nodes"]:
            try:
                update = await node["func"](state)
                # Merge update into state
                for key, value in update.items():
                    if key in state and isinstance(state[key], list) and isinstance(value, list):
                        state[key] = list(dict.fromkeys(state[key] + value))
                    elif key in state and isinstance(state[key], dict) and isinstance(value, dict):
                        state[key] = {**state[key], **value}
                    else:
                        state[key] = value
            except Exception as e:
                state["status"] = "failed"
                state["errors"] = state.get("errors", []) + [f"{node['name']}: {str(e)}"]
                break

        return state
