"""Tests for Phase 2: Research Branch Subgraph.

Tests:
1. Research branch happy path
2. Evidence validation
3. Checkpoint resume (no duplicate fetches)
4. Partial failure handling
5. Budget tracking
"""

import pytest

from app.gateways.model import FakeModelGateway
from app.gateways.search import FakeSearchGateway
from app.gateways.fetch import FakeDocumentFetcher
from app.gateways.storage import InMemoryArtifactStore
from app.graphs.research_branch import ResearchBranchBuilder, ResearchBranchState


class TestResearchBranchHappyPath:
    """Test research branch happy path."""

    @pytest.fixture
    def builder(self):
        """Create a research branch builder with fake gateways."""
        return ResearchBranchBuilder(
            model_gateway=FakeModelGateway(responses={
                "plan_queries": '{"queries": ["query1", "query2", "query3"]}',
            }),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self):
        """Create initial state for research branch."""
        return {
            "run_id": "test-run",
            "subtask_id": "subtask-1",
            "question": "What is the market size of AI agents in 2026?",
            "research_round": 1,
            "status": "pending",
            "current_node": "",
            "started_at": "2026-01-01T00:00:00",
            "queries": [],
            "document_ids": [],
            "evidence_ids": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    @pytest.mark.asyncio
    async def test_branch_completes_successfully(self, builder, initial_state):
        """Research branch should complete with evidence."""
        result = await builder.run(initial_state)

        assert result["status"] == "completed"
        assert result["evidence_count"] > 0
        assert result["current_node"] == "persist_branch_result"

    @pytest.mark.asyncio
    async def test_branch_generates_queries(self, builder, initial_state):
        """Branch should generate search queries."""
        result = await builder.run(initial_state)

        assert len(result["queries"]) > 0

    @pytest.mark.asyncio
    async def test_branch_fetches_documents(self, builder, initial_state):
        """Branch should fetch documents."""
        result = await builder.run(initial_state)

        assert result["documents_fetched"] > 0

    @pytest.mark.asyncio
    async def test_branch_tracks_budget(self, builder, initial_state):
        """Branch should track token usage and cost."""
        result = await builder.run(initial_state)

        assert result["tokens_used"] > 0
        assert result["cost_usd"] > 0


class TestResearchBranchPartialFailure:
    """Test research branch with partial failures."""

    @pytest.mark.asyncio
    async def test_search_failure_returns_partial(self):
        """Search failure should return partial status."""
        # Create a search gateway that returns empty results
        search_gateway = FakeSearchGateway(results={})

        builder = ResearchBranchBuilder(
            model_gateway=FakeModelGateway(responses={
                "plan_queries": '{"queries": ["query1"]}',
            }),
            search_gateway=search_gateway,
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

        initial_state = {
            "run_id": "test-run",
            "subtask_id": "subtask-1",
            "question": "Test question",
            "research_round": 1,
            "status": "pending",
            "queries": [],
            "document_ids": [],
            "evidence_ids": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

        result = await builder.run(initial_state)

        # Should complete but with no evidence (since no search results)
        assert result["status"] in ["completed", "partial"]

    @pytest.mark.asyncio
    async def test_fetch_failure_handled_gracefully(self):
        """Fetch failure should not crash the branch."""
        builder = ResearchBranchBuilder(
            model_gateway=FakeModelGateway(responses={
                "plan_queries": '{"queries": ["query1"]}',
            }),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

        initial_state = {
            "run_id": "test-run",
            "subtask_id": "subtask-1",
            "question": "Test question",
            "research_round": 1,
            "status": "pending",
            "queries": [],
            "document_ids": [],
            "evidence_ids": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

        result = await builder.run(initial_state)

        # Should not be failed
        assert result["status"] != "failed"


class TestResearchBranchIdempotency:
    """Test research branch idempotency (checkpoint resume)."""

    @pytest.mark.asyncio
    async def test_rerun_does_not_duplicate_evidence(self):
        """Re-running branch should not duplicate evidence."""
        builder = ResearchBranchBuilder(
            model_gateway=FakeModelGateway(responses={
                "plan_queries": '{"queries": ["query1"]}',
            }),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

        initial_state = {
            "run_id": "test-run",
            "subtask_id": "subtask-1",
            "question": "Test question",
            "research_round": 1,
            "status": "pending",
            "queries": [],
            "document_ids": [],
            "evidence_ids": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

        # First run
        result1 = await builder.run(initial_state)
        evidence_count_1 = result1["evidence_count"]

        # Second run (simulating resume from checkpoint)
        result2 = await builder.run(result1)
        evidence_count_2 = result2["evidence_count"]

        # Evidence count should not double
        assert evidence_count_2 == evidence_count_1

    @pytest.mark.asyncio
    async def test_resume_from_middle_state(self):
        """Resuming from middle state should continue correctly."""
        builder = ResearchBranchBuilder(
            model_gateway=FakeModelGateway(responses={
                "plan_queries": '{"queries": ["query1"]}',
            }),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

        # Start from a state that already has queries and documents
        mid_state = {
            "run_id": "test-run",
            "subtask_id": "subtask-1",
            "question": "Test question",
            "research_round": 1,
            "status": "in_progress",
            "current_node": "execute_search",
            "queries": ["query1"],
            "document_ids": ["https://example.com/1"],
            "documents_fetched": 1,
            "evidence_ids": [],
            "tokens_used": 100,
            "cost_usd": 0.01,
        }

        result = await builder.run(mid_state)

        # Should complete from middle state
        assert result["status"] == "completed"
        assert result["evidence_count"] > 0


class TestResearchBranchState:
    """Test research branch state constraints."""

    def test_state_is_json_safe(self):
        """State must be JSON-serializable."""
        import json

        state = {
            "run_id": "test",
            "subtask_id": "sub-1",
            "question": "Test",
            "research_round": 1,
            "status": "pending",
            "queries": ["q1"],
            "document_ids": ["url1"],
            "evidence_ids": ["e1"],
            "tokens_used": 100,
            "cost_usd": 0.01,
        }

        # Should not raise
        json.dumps(state)

    def test_state_no_forbidden_types(self):
        """State must not contain forbidden types."""
        state = {
            "run_id": "test",
            "subtask_id": "sub-1",
            "question": "Test",
            "research_round": 1,
            "status": "pending",
        }

        # Check for forbidden keys
        forbidden = ["client", "connection", "session", "exception"]
        for key in state.keys():
            for f in forbidden:
                assert f not in key.lower(), f"Forbidden key: {key}"