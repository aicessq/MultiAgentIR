"""Debug test for hierarchical graph execution."""

import pytest
from app.gateways.model import FakeModelGateway
from app.gateways.search import FakeSearchGateway
from app.gateways.fetch import FakeDocumentFetcher
from app.gateways.storage import InMemoryArtifactStore
from app.graphs.hierarchical import HierarchicalGraphBuilder


@pytest.mark.asyncio
async def test_debug_execution():
    """Debug the execution flow."""
    builder = HierarchicalGraphBuilder(
        model_gateway=FakeModelGateway(),
        search_gateway=FakeSearchGateway(),
        document_fetcher=FakeDocumentFetcher(),
        artifact_store=InMemoryArtifactStore(),
    )

    initial_state = {
        "run_id": "test-run",
        "query": "Test query",
        "task_type": "general",
        "config_snapshot_id": "test-config",
        "status": "pending",
        "pending_subtasks": [],
        "completed_subtask_ids": [],
        "failed_subtask_ids": [],
        "branch_results": {},
        "evidence_ids": [],
        "analysis_revision_id": None,
        "analysis_revisions": [],
        "critique_revision_id": None,
        "critique_revisions": [],
        "critique_findings": [],
        "followup_queries": [],
        "report_revision_id": None,
        "report_revisions": [],
        "validation_result": None,
        "validation_decision": None,
        "repair_instructions": [],
        "repair_count": 0,
        "max_repairs": 2,
        "research_round": 0,
        "max_research_rounds": 2,
        "current_wave": 0,
        "max_waves": 3,
        "wave_size": 2,
        "terminal_reason": None,
        "warnings": [],
        "errors": [],
    }

    result = await builder.run(initial_state)
    
    print(f"\nFinal status: {result['status']}")
    print(f"Errors: {result.get('errors', [])}")
    print(f"Evidence IDs: {result.get('evidence_ids', [])}")
    print(f"Analysis ID: {result.get('analysis_revision_id')}")
    print(f"Report ID: {result.get('report_revision_id')}")
    print(f"Branch results: {result.get('branch_results', {})}")
    print(f"Completed subtasks: {result.get('completed_subtask_ids', [])}")
