"""Research Branch Subgraph.

A single research branch processes one subtask:
1. Plan search queries
2. Execute search
3. Fetch documents
4. Extract evidence
5. Verify evidence
6. Persist result

Usage:
    from app.graphs.research_branch import ResearchBranchBuilder
    
    builder = ResearchBranchBuilder(
        model_gateway=model_gateway,
        search_gateway=search_gateway,
        document_fetcher=document_fetcher,
        artifact_store=artifact_store,
    )
    result = await builder.run(initial_state)
"""

from app.graphs.research_branch.state import ResearchBranchState
from app.graphs.research_branch.nodes import (
    plan_queries_node,
    execute_search_node,
    fetch_documents_node,
    extract_evidence_node,
    verify_evidence_node,
    persist_branch_result_node,
)
from app.graphs.research_branch.builder import ResearchBranchBuilder

__all__ = [
    "ResearchBranchState",
    "plan_queries_node",
    "execute_search_node",
    "fetch_documents_node",
    "extract_evidence_node",
    "verify_evidence_node",
    "persist_branch_result_node",
    "ResearchBranchBuilder",
]