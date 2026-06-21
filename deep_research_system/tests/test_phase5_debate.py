"""Tests for Phase 5: Debate Graph.

Tests:
1. Debate graph happy path
2. Debate position enum usage
3. Cross-examination conflict detection
4. Synthesis claim graph
5. Quality gate failure
6. State JSON safety
"""

import pytest

from app.domain.enums import DebatePosition, RunStatus
from app.gateways.model import FakeModelGateway
from app.gateways.search import FakeSearchGateway
from app.gateways.fetch import FakeDocumentFetcher
from app.gateways.storage import InMemoryArtifactStore
from app.graphs.debate import DebateGraphBuilder, DebateState


class TestDebateHappyPath:
    """Test debate graph happy path."""

    @pytest.fixture
    def builder(self):
        return DebateGraphBuilder(
            model_gateway=FakeModelGateway(),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self) -> DebateState:
        return {
            "run_id": "test-run-1",
            "query": "Should AI be regulated?",
            "task_type": "open_question",
            "config_snapshot_id": "config-1",
            "status": "running",
            "hypotheses": [],
            "current_hypothesis_index": 0,
            "max_hypotheses": 3,
            "debate_positions": {},
            "debate_results": {},
            "completed_branch_ids": [],
            "failed_branch_ids": [],
            "evidence_ids": [],
            "cross_examine_findings": [],
            "cross_examine_revision_id": None,
            "synthesis_id": None,
            "synthesis_revisions": [],
            "claim_graph": [],
            "report_revision_id": None,
            "report_revisions": [],
            "validation_result": None,
            "validation_decision": None,
            "repair_instructions": [],
            "repair_count": 0,
            "max_repairs": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

    @pytest.mark.asyncio
    async def test_debate_completes_successfully(self, builder, initial_state):
        """Debate graph should complete successfully."""
        result = await builder.run(initial_state)
        assert result["status"] == RunStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_debate_generates_hypotheses(self, builder, initial_state):
        """Debate graph should generate hypotheses."""
        result = await builder.run(initial_state)
        assert len(result["hypotheses"]) > 0

    @pytest.mark.asyncio
    async def test_debate_generates_evidence(self, builder, initial_state):
        """Debate graph should generate evidence from branches."""
        result = await builder.run(initial_state)
        assert len(result["evidence_ids"]) > 0

    @pytest.mark.asyncio
    async def test_debate_generates_synthesis(self, builder, initial_state):
        """Debate graph should produce synthesis."""
        result = await builder.run(initial_state)
        assert result["synthesis_id"] is not None
        assert len(result["claim_graph"]) > 0


class TestDebatePositions:
    """Test debate position enum usage."""

    @pytest.fixture
    def builder(self):
        return DebateGraphBuilder(
            model_gateway=FakeModelGateway(),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self) -> DebateState:
        return {
            "run_id": "test-run-2",
            "query": "Test query",
            "task_type": "open_question",
            "config_snapshot_id": "config-1",
            "status": "running",
            "hypotheses": [],
            "current_hypothesis_index": 0,
            "max_hypotheses": 3,
            "debate_positions": {},
            "debate_results": {},
            "completed_branch_ids": [],
            "failed_branch_ids": [],
            "evidence_ids": [],
            "cross_examine_findings": [],
            "cross_examine_revision_id": None,
            "synthesis_id": None,
            "synthesis_revisions": [],
            "claim_graph": [],
            "report_revision_id": None,
            "report_revisions": [],
            "validation_result": None,
            "validation_decision": None,
            "repair_instructions": [],
            "repair_count": 0,
            "max_repairs": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

    @pytest.mark.asyncio
    async def test_debate_positions_use_enum(self, builder, initial_state):
        """Debate positions should use DebatePosition enum values."""
        result = await builder.run(initial_state)
        for position in result.get("debate_positions", {}).values():
            assert position in {p.value for p in DebatePosition}

    @pytest.mark.asyncio
    async def test_all_three_positions_present(self, builder, initial_state):
        """All three debate positions should be present."""
        result = await builder.run(initial_state)
        positions = set(result.get("debate_positions", {}).values())
        assert DebatePosition.SUPPORT.value in positions
        assert DebatePosition.OPPOSE.value in positions
        assert DebatePosition.ALTERNATIVE.value in positions


class TestCrossExamination:
    """Test cross-examination conflict detection."""

    @pytest.fixture
    def builder(self):
        return DebateGraphBuilder(
            model_gateway=FakeModelGateway(),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self) -> DebateState:
        return {
            "run_id": "test-run-3",
            "query": "Test query",
            "task_type": "open_question",
            "config_snapshot_id": "config-1",
            "status": "running",
            "hypotheses": [],
            "current_hypothesis_index": 0,
            "max_hypotheses": 3,
            "debate_positions": {},
            "debate_results": {},
            "completed_branch_ids": [],
            "failed_branch_ids": [],
            "evidence_ids": [],
            "cross_examine_findings": [],
            "cross_examine_revision_id": None,
            "synthesis_id": None,
            "synthesis_revisions": [],
            "claim_graph": [],
            "report_revision_id": None,
            "report_revisions": [],
            "validation_result": None,
            "validation_decision": None,
            "repair_instructions": [],
            "repair_count": 0,
            "max_repairs": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

    @pytest.mark.asyncio
    async def test_cross_examine_detects_conflicts(self, builder, initial_state):
        """Cross-examination should detect conflicts between positions."""
        result = await builder.run(initial_state)
        findings = result.get("cross_examine_findings", [])
        assert len(findings) > 0
        # Should detect conflict between support and oppose
        conflict_found = any(f.get("type") == "conflict" for f in findings)
        assert conflict_found

    @pytest.mark.asyncio
    async def test_cross_examine_produces_revision(self, builder, initial_state):
        """Cross-examination should produce a revision ID."""
        result = await builder.run(initial_state)
        assert result["cross_examine_revision_id"] is not None
        assert result["cross_examine_revision_id"].startswith("cross-examine-")


class TestSynthesis:
    """Test synthesis claim graph."""

    @pytest.fixture
    def builder(self):
        return DebateGraphBuilder(
            model_gateway=FakeModelGateway(),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self) -> DebateState:
        return {
            "run_id": "test-run-4",
            "query": "Test query",
            "task_type": "open_question",
            "config_snapshot_id": "config-1",
            "status": "running",
            "hypotheses": [],
            "current_hypothesis_index": 0,
            "max_hypotheses": 3,
            "debate_positions": {},
            "debate_results": {},
            "completed_branch_ids": [],
            "failed_branch_ids": [],
            "evidence_ids": [],
            "cross_examine_findings": [],
            "cross_examine_revision_id": None,
            "synthesis_id": None,
            "synthesis_revisions": [],
            "claim_graph": [],
            "report_revision_id": None,
            "report_revisions": [],
            "validation_result": None,
            "validation_decision": None,
            "repair_instructions": [],
            "repair_count": 0,
            "max_repairs": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

    @pytest.mark.asyncio
    async def test_synthesis_claim_graph_has_positions(self, builder, initial_state):
        """Claim graph should include position information."""
        result = await builder.run(initial_state)
        claim_graph = result.get("claim_graph", [])
        assert len(claim_graph) > 0
        for claim in claim_graph:
            assert "position" in claim
            assert claim["position"] in {p.value for p in DebatePosition}

    @pytest.mark.asyncio
    async def test_synthesis_tracks_evidence_counts(self, builder, initial_state):
        """Claim graph should track evidence counts per branch."""
        result = await builder.run(initial_state)
        claim_graph = result.get("claim_graph", [])
        for claim in claim_graph:
            assert "evidence_count" in claim
            assert isinstance(claim["evidence_count"], int)


class TestQualityGate:
    """Test quality gate failure."""

    def test_validation_router_pass(self):
        """Validation router should route to finalize on pass."""
        from app.graphs.debate.nodes import validation_router

        state = {
            "validation_decision": "pass",
            "repair_count": 0,
            "max_repairs": 2,
        }
        result = validation_router(state)
        assert result == "finalize_debate"

    def test_validation_router_repair(self):
        """Validation router should route to repair when repairable."""
        from app.graphs.debate.nodes import validation_router

        state = {
            "validation_decision": "repair",
            "repair_count": 0,
            "max_repairs": 2,
        }
        result = validation_router(state)
        assert result == "repair_report"

    def test_validation_router_max_repairs(self):
        """Validation router should route to quality_gate_failed when max repairs reached."""
        from app.graphs.debate.nodes import validation_router

        state = {
            "validation_decision": "repair",
            "repair_count": 2,
            "max_repairs": 2,
        }
        result = validation_router(state)
        assert result == "quality_gate_failed"

    def test_quality_failure_node(self):
        """Quality gate failure node should set failed_quality_gate status."""
        import asyncio
        from app.graphs.debate.nodes import quality_gate_failed_node

        state = {}
        result = asyncio.run(quality_gate_failed_node(state))
        assert result["status"] == RunStatus.FAILED_QUALITY_GATE.value
        assert result["terminal_reason"] == "quality_gate_failed"


class TestStateJsonSafe:
    """Test debate state is JSON-safe."""

    def test_debate_state_is_json_safe(self):
        """Debate state should be JSON serializable."""
        import json

        state = {
            "run_id": "test",
            "query": "test query",
            "task_type": "open_question",
            "config_snapshot_id": "config-1",
            "status": "running",
            "hypotheses": ["h1", "h2"],
            "current_hypothesis_index": 0,
            "max_hypotheses": 3,
            "debate_positions": {"b1": "support"},
            "debate_results": {"b1": {"evidence_ids": ["e1"]}},
            "completed_branch_ids": ["b1"],
            "failed_branch_ids": [],
            "evidence_ids": ["e1"],
            "cross_examine_findings": [{"type": "conflict"}],
            "cross_examine_revision_id": "cx-1",
            "synthesis_id": "syn-1",
            "synthesis_revisions": ["syn-1"],
            "claim_graph": [{"position": "support", "evidence_count": 1}],
            "report_revision_id": "rpt-1",
            "report_revisions": ["rpt-1"],
            "validation_result": {"score": 90, "decision": "pass"},
            "validation_decision": "pass",
            "repair_instructions": [],
            "repair_count": 0,
            "max_repairs": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

        # Should not raise
        json.dumps(state)

    def test_state_no_forbidden_types(self):
        """Debate state should not contain forbidden types."""
        state = {
            "run_id": "test",
            "query": "test query",
            "status": "running",
            "debate_positions": {},
            "debate_results": {},
        }

        # Check for forbidden keys
        forbidden = ["client", "connection", "session", "exception"]
        for key in state:
            for f in forbidden:
                assert f not in key.lower(), f"Forbidden key: {key}"
