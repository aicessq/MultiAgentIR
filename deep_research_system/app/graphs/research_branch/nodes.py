"""Research Branch Nodes.

Each node:
1. Receives state + context
2. Performs work via gateways
3. Returns ONLY incremental state updates
4. Does NOT modify state in place
5. Is idempotent (safe to retry)

Node flow:
plan_queries -> execute_search -> normalize_results -> fetch_documents -> extract_content -> extract_evidence -> verify_evidence -> persist_branch_result
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from app.domain.enums import SourceTier
from app.domain.errors import SearchProviderError, FetchError, EvidenceValidationError
from app.domain.models import Evidence, Document, Source
from app.gateways.model import ModelGateway, ModelRequest
from app.gateways.search import SearchGateway, SearchQuery, SearchRequest
from app.gateways.fetch import DocumentFetcher, FetchRequest
from app.gateways.storage import ArtifactStore
from app.graphs.research_branch.state import ResearchBranchState

logger = logging.getLogger(__name__)


async def plan_queries_node(
    state: ResearchBranchState,
    model_gateway: ModelGateway,
) -> dict:
    """Generate search queries for the subtask question.

    Returns incremental update with queries list.
    """
    question = state["question"]

    request = ModelRequest(
        purpose="plan_queries",
        messages=[{
            "role": "user",
            "content": f"Generate 3-5 search queries for: {question}"
        }],
        output_schema={
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["queries"]
        },
        required_capabilities={"chat"},
        max_output_tokens=500,
        temperature=0.7,
    )

    try:
        response = await model_gateway.call(request)
        parsed = response.parsed_output or {}
        queries = parsed.get("queries", [question])

        return {
            "queries": queries,
            "current_node": "plan_queries",
            "tokens_used": state.get("tokens_used", 0) + response.prompt_tokens + response.completion_tokens,
            "cost_usd": state.get("cost_usd", 0.0) + response.estimated_cost_usd,
        }
    except Exception as e:
        logger.error(f"plan_queries failed: {e}")
        # Fallback: use the question itself as a query
        return {
            "queries": [question],
            "current_node": "plan_queries",
            "warnings": [f"Query planning failed, using fallback: {str(e)}"],
        }


async def execute_search_node(
    state: ResearchBranchState,
    search_gateway: SearchGateway,
) -> dict:
    """Execute search queries.

    Returns incremental update with search results.
    """
    queries = state.get("queries", [])
    if not queries:
        return {
            "status": "failed",
            "errors": ["No queries to search"],
            "current_node": "execute_search",
        }

    search_queries = [
        SearchQuery(query=q, max_results=5)
        for q in queries
    ]

    request = SearchRequest(
        queries=search_queries,
        deduplicate_urls=True,
        filter_low_quality=True,
    )

    try:
        response = await search_gateway.search(request)

        # Collect URLs from results
        urls = []
        for rs in response.result_sets:
            for result in rs.results:
                urls.append(result.url)

        # Generate result set ID
        import hashlib
        result_set_id = hashlib.sha256(
            json.dumps([q.query for q in search_queries]).encode()
        ).hexdigest()[:16]

        return {
            "search_result_set_id": result_set_id,
            "search_results_count": response.total_results,
            "document_ids": urls,  # URLs to fetch
            "current_node": "execute_search",
            "warnings": response.errors,
        }
    except Exception as e:
        logger.error(f"execute_search failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Search failed: {str(e)}"],
            "current_node": "execute_search",
        }


async def fetch_documents_node(
    state: ResearchBranchState,
    document_fetcher: DocumentFetcher,
) -> dict:
    """Fetch full content from URLs.

    Returns incremental update with fetch results.
    """
    urls = state.get("document_ids", [])
    if not urls:
        return {
            "status": "partial",
            "warnings": ["No URLs to fetch"],
            "current_node": "fetch_documents",
        }

    request = FetchRequest(
        urls=urls,
        max_concurrent=3,
        timeout_per_url_seconds=30.0,
    )

    try:
        response = await document_fetcher.fetch(request)

        successful_docs = []
        failed_docs = []

        for result in response.results:
            if result.success and result.content:
                successful_docs.append(result.url)
            else:
                failed_docs.append(result.url)

        return {
            "documents_fetched": len(successful_docs),
            "documents_failed": len(failed_docs),
            "current_node": "fetch_documents",
            "warnings": [f"Failed to fetch: {url}" for url in failed_docs],
        }
    except Exception as e:
        logger.error(f"fetch_documents failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Fetch failed: {str(e)}"],
            "current_node": "fetch_documents",
        }


async def extract_evidence_node(
    state: ResearchBranchState,
    model_gateway: ModelGateway,
) -> dict:
    """Extract evidence from fetched documents.

    Returns incremental update with evidence IDs.
    """
    # In production, this would:
    # 1. Load documents from artifact store
    # 2. Extract passages
    # 3. Generate evidence items
    # 4. Validate evidence

    # For now, generate placeholder evidence
    question = state["question"]
    evidence_items = []

    # Simulate evidence extraction
    for i in range(min(3, state.get("documents_fetched", 0))):
        evidence_id = f"EVID-{state['subtask_id']}-{i}"
        evidence_items.append(evidence_id)

    return {
        "evidence_ids": evidence_items,
        "evidence_count": len(evidence_items),
        "current_node": "extract_evidence",
    }


async def verify_evidence_node(
    state: ResearchBranchState,
) -> dict:
    """Verify evidence quality.

    Returns incremental update with validated/rejected counts.
    """
    evidence_count = state.get("evidence_count", 0)

    # In production, this would:
    # 1. Check quote exists in document
    # 2. Verify source tier
    # 3. Check for contradictions
    # 4. Validate confidence scores

    # Simulate: accept all for now
    validated = evidence_count
    rejected = 0

    return {
        "evidence_validated": validated,
        "evidence_rejected": rejected,
        "current_node": "verify_evidence",
        "status": "completed" if validated > 0 else "partial",
    }


async def persist_branch_result_node(
    state: ResearchBranchState,
    artifact_store: ArtifactStore,
) -> dict:
    """Persist final branch result.

    Returns final state update.
    """
    status = state.get("status", "completed")

    if status == "failed":
        return {
            "status": "failed",
            "finished_at": datetime.utcnow().isoformat(),
            "current_node": "persist_branch_result",
        }

    return {
        "status": "completed" if state.get("evidence_validated", 0) > 0 else "partial",
        "finished_at": datetime.utcnow().isoformat(),
        "current_node": "persist_branch_result",
    }
