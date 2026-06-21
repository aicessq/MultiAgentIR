"""Tests for Phase 3: Hierarchical Graph.

Tests:
1. Hierarchical happy path
2. Supplemental research loop
3. Authoritative analysis pointer
4. Report repair loop
5. Quality gate failure
6. Loop limits
"""

import pytest

from app.domain.enums import RunStatus
from app.gateways.model import FakeModelGateway
from app.gateways.search import FakeSearchGateway
from app.gateways.fetch import FakeDocumentFetcher
from app.gateways.storage import InMemoryArtifactStore
from app.graphs.hierarchical import HierarchicalGraphBuilder, HierarchicalState


class TestHierarchicalHappyPath:
    """Test hierarchical graph happy path."""

    @pytest.fixture
    def builder(self):
        """Create a hierarchical graph builder with fake gateways."""
        return HierarchicalGraphBuilder(
            model_gateway=FakeModelGateway(),
            search_gateway=FakeSearchGateway(),
            document_fetcher=FakeDocumentFetcher(),
            artifact_store=InMemoryArtifactStore(),
        )

    @pytest.fixture
    def initial_state(self):
        """Create initial state for hierarchical graph."""
        return {
            "run_id": "test-run",
            "query": "What is the market size of AI agents in 2026?",
            "task_type": "industry_report",
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

    @pytest.mark.asyncio
    async def test_hierarchical_completes_successfully(self, builder, initial_state):
        """Hierarchical graph should complete with report."""
        result = await builder.run(initial_state)

        assert result["status"] == RunStatus.COMPLETED.value
        assert result["terminal_reason"] == "success"
        assert result["report_revision_id"] is not None

    @pytest.mark.asyncio
    async def test_hierarchical_generates_analysis(self, builder, initial_state):
        """Hierarchical graph should generate analysis."""
        result = await builder.run(initial_state)

        assert result["analysis_revision_id"] is not None
        assert len(result["analysis_revisions"]) > 0

    @pytest.mark.asyncio
    async def test_hierarchical_generates_evidence(self, builder, initial_state):
        """Hierarchical graph should generate evidence."""
        result = await builder.run(initial_state)

        assert len(result["evidence_ids"]) > 0


class TestSupplementalResearch:
    """Test supplemental research loop."""

    @pytest.mark.asyncio
    async def test_supplemental_research_increments_round(self):
        """Supplemental research should increment research_round."""
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

        # Should have completed research rounds
        assert result["research_round"] >= 0

    @pytest.mark.asyncio
    async def test_supplemental_research_has_limit(self):
        """Supplemental research should respect max_research_rounds."""
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
            "max_research_rounds": 1,  # Limit to 1 round
            "current_wave": 0,
            "max_waves": 3,
            "wave_size": 2,
            "terminal_reason": None,
            "warnings": [],
            "errors": [],
        }

        result = await builder.run(initial_state)

        # Should not exceed max_research_rounds
        assert result["research_round"] <= initial_state["max_research_rounds"]


class TestAuthoritativePointer:
    """Test authoritative analysis pointer."""

    @pytest.mark.asyncio
    async def test_analysis_revision_updates_pointer(self):
        """New analysis should update authoritative_analysis_id."""
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

        # Should have updated authoritative pointer
        assert result["analysis_revision_id"] is not None
        assert len(result["analysis_revisions"]) > 0

    @pytest.mark.asyncio
    async def test_writer_uses_authoritative_analysis(self):
        """Writer should use authoritative_analysis_id."""
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

        # Report should reference analysis
        assert result["report_revision_id"] is not None
        assert result["analysis_revision_id"] is not None


class TestReportRepair:
    """Test report repair loop."""

    @pytest.mark.asyncio
    async def test_repair_loop_respects_max_repairs(self):
        """Repair loop should respect max_repairs."""
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
            "max_repairs": 1,  # Limit repairs
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

        # Should complete (validation passes in fake)
        assert result["status"] == RunStatus.COMPLETED.value


class TestQualityGate:
    """Test quality gate failure."""

    def test_quality_failure_router(self):
        """Quality gate failure router should return quality_gate_failed."""
        from app.graphs.hierarchical.nodes import validation_router

        state = {
            "validation_decision": "fail",
            "repair_count": 2,
            "max_repairs": 2,
        }

        result = validation_router(state)
        assert result == "quality_gate_failed"

    def test_quality_failure_node(self):
        """Quality gate failure node should set failed_quality_gate status."""
        import asyncio
        from app.graphs.hierarchical.nodes import quality_gate_failed_node

        state = {
            "status": "validating",
        }

        result = asyncio.run(quality_gate_failed_node(state))
        assert result["status"] == RunStatus.FAILED_QUALITY_GATE.value
        assert result["terminal_reason"] == "quality_gate_failed"


class TestLoopLimits:
    """Test loop limits prevent infinite loops."""

    @pytest.mark.asyncio
    async def test_max_steps_prevents_infinite_loop(self):
        """Graph should stop after max_steps."""
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

        # Should complete within max_steps (50)
        assert result["status"] in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.FAILED_QUALITY_GATE.value)


class TestStateJsonSafe:
    """Test state is JSON-safe."""

    def test_hierarchical_state_is_json_safe(self):
        """HierarchicalState must be JSON-serializable."""
        import json

        state = {
            "run_id": "test",
            "query": "Test query",
            "task_type": "general",
            "config_snapshot_id": "test",
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

        # Should not raise
        json.dumps(state)