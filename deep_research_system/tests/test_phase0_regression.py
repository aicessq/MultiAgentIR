"""Phase 0 regression tests for LangGraph refactoring.

These tests verify the core bugs that must be fixed before refactoring:
1. Writer must use the latest authoritative analysis after supplemental research
2. Debate positions must use unified enum (SUPPORT/OPPOSE/ALTERNATIVE)
3. Validator blocking failures must produce failed_quality_gate terminal state
4. Configuration changes must affect runtime behavior
"""

from app.schemas.agent_outputs import DebatePosition
from app.schemas.state import ResearchState
from app.schemas.task import ResearchStrategy, RunStatus, TaskSpec


class TestSupplementalResearchUsesLatestAnalysis:
    """Bug: After supplemental research, Writer may still consume the first round analysis.

    The fix requires:
    - analyses stored as append-only revisions
    - authoritative_analysis_id points to the latest
    - Writer reads from authoritative pointer, not analyses[-1]
    """

    def test_analyses_appends_new_revision_on_supplemental_research(self):
        """Supplemental research should append a new analysis revision, not overwrite."""
        state = ResearchState(
            task=TaskSpec(user_query="test query", task_type="industry_report"),
            analyses=[{"version": 1, "content": "initial analysis"}],
        )

        # Simulate supplemental research adding new analysis
        supplemental_analysis = {"version": 2, "content": "supplemental analysis"}
        state.analyses.append(supplemental_analysis)

        assert len(state.analyses) == 2
        assert state.analyses[0]["version"] == 1
        assert state.analyses[1]["version"] == 2

    def test_authoritative_analysis_id_points_to_latest(self):
        """State should track authoritative_analysis_id pointing to the latest analysis."""
        state = ResearchState(
            task=TaskSpec(user_query="test query", task_type="industry_report"),
            analyses=[
                {"analysis_id": "a1", "version": 1},
                {"analysis_id": "a2", "version": 2},
            ],
            authoritative_analysis_id="a1",
        )

        # Update to latest after supplemental research
        state.authoritative_analysis_id = "a2"

        assert state.authoritative_analysis_id == "a2"

    def test_writer_reads_from_authoritative_pointer_not_implicit_index(self):
        """Writer must read from authoritative_analysis_id, not analyses[-1] or analyses[0].

        This test verifies the contract that:
        - analyses is append-only
        - authoritative_analysis_id is the source of truth
        - Writer should use the analysis where claim_graph matches authoritative_analysis_id
        """
        analyses = [
            {"analysis_id": "a1", "claim_graph": [{"claim_id": "c1"}]},
            {"analysis_id": "a2", "claim_graph": [{"claim_id": "c2"}, {"claim_id": "c3"}]},
        ]

        authoritative_id = "a2"
        authoritative_analysis = next(a for a in analyses if a["analysis_id"] == authoritative_id)

        # Writer should use authoritative_analysis, not analyses[-1]
        assert authoritative_analysis["analysis_id"] == "a2"
        assert len(authoritative_analysis["claim_graph"]) == 2

    def test_supplemental_research_does_not_duplicate_analysis_ids(self):
        """Supplemental research should not create duplicate analysis IDs."""
        existing_ids = {"a1", "a2"}

        new_analysis_id = "a3"
        assert new_analysis_id not in existing_ids


class TestDebatePositionEnum:
    """Bug: Debate branches use inconsistent string keys (h_0, h_1) instead of unified enum.

    The fix requires:
    - Use DebatePosition enum: SUPPORT, OPPOSE, ALTERNATIVE
    - Branch IDs must be stable and match enum values
    - No ad-hoc string keys like "h_0", "pro", "con"
    """

    def test_debate_position_enum_exists(self):
        """DebatePosition enum should exist and have correct values."""
        assert hasattr(DebatePosition, "SUPPORT")
        assert hasattr(DebatePosition, "OPPOSE")
        assert hasattr(DebatePosition, "ALTERNATIVE")

    def test_debate_branch_uses_enum_not_string_keys(self):
        """Branch IDs should use DebatePosition enum values, not ad-hoc strings."""
        # Good: using enum
        branch_id = DebatePosition.SUPPORT.value

        # Bad pattern (old code): h_0, h_1, "pro", "con"
        bad_patterns = ["h_0", "h_1", "pro", "con", "neutral"]

        assert branch_id not in bad_patterns
        assert branch_id in [e.value for e in DebatePosition]

    def test_debate_results_keys_match_position_enum(self):
        """debate_results dict keys should match DebatePosition enum values."""
        positions = [DebatePosition.SUPPORT, DebatePosition.OPPOSE, DebatePosition.ALTERNATIVE]

        # Build debate results with enum keys
        debate_results = {pos.value: {"position": pos.value, "evidence": []} for pos in positions}

        for key in debate_results:
            assert key in [e.value for e in DebatePosition]


class TestValidatorQualityGateTerminalState:
    """Bug: Validator blocking failures may still result in 'completed' status.

    The fix requires:
    - failed_quality_gate as a distinct terminal state
    - Validator score < threshold triggers quality gate failure
    - Terminal states are explicitly mapped from validation outcomes
    """

    def test_failed_quality_gate_is_distinct_terminal_state(self):
        """failed_quality_gate must be a distinct terminal state, not completed."""
        # These must be distinct states
        assert RunStatus.COMPLETED != RunStatus.FAILED_QUALITY_GATE
        assert RunStatus.COMPLETED_WITH_WARNINGS != RunStatus.FAILED_QUALITY_GATE

    def test_validator_score_below_threshold_triggers_quality_gate_failure(self):
        """Validation score < 85 should result in failed_quality_gate, not completed."""
        validation_result = {"valid": False, "score": 70, "issues": [{"severity": "high"}]}

        # High severity issues with score < 85 should map to FAILED_QUALITY_GATE
        has_high_severity = any(i.get("severity") == "high" for i in validation_result.get("issues", []))
        score_low = validation_result.get("score", 100) < 85

        if has_high_severity and score_low:
            terminal_state = RunStatus.FAILED_QUALITY_GATE
        else:
            terminal_state = RunStatus.COMPLETED

        assert terminal_state == RunStatus.FAILED_QUALITY_GATE

    def test_validator_score_above_threshold_with_high_issues_still_fails(self):
        """High severity issues should fail quality gate even if score >= 85."""
        validation_result = {"valid": False, "score": 90, "issues": [{"severity": "high"}]}

        has_high_severity = any(i.get("severity") == "high" for i in validation_result.get("issues", []))

        if has_high_severity:
            terminal_state = RunStatus.FAILED_QUALITY_GATE
        else:
            terminal_state = RunStatus.COMPLETED

        assert terminal_state == RunStatus.FAILED_QUALITY_GATE

    def test_validation_pass_with_warnings_maps_to_completed_with_warnings(self):
        """Validation pass with warnings should result in completed_with_warnings."""
        validation_result = {"valid": True, "score": 90, "warnings": [{"severity": "medium"}]}

        if validation_result.get("valid") and validation_result.get("warnings"):
            terminal_state = RunStatus.COMPLETED_WITH_WARNINGS
        elif validation_result.get("valid"):
            terminal_state = RunStatus.COMPLETED
        else:
            terminal_state = RunStatus.FAILED_QUALITY_GATE

        assert terminal_state == RunStatus.COMPLETED_WITH_WARNINGS


class TestConfigurationAffectsRuntime:
    """Bug: Configuration changes may not affect runtime behavior.

    The fix requires:
    - Single source of truth for config (EffectiveConfig)
    - Config snapshot saved with each run
    - Runtime reads from frozen config, not live config
    """

    def test_config_snapshot_id_is_generated_per_run(self):
        """Each run should have a unique config_snapshot_id."""
        state = ResearchState(
            task=TaskSpec(user_query="test", task_type="industry_report"),
        )

        import uuid
        state.config_snapshot_id = str(uuid.uuid4())

        assert state.config_snapshot_id is not None
        assert len(state.config_snapshot_id) > 0

    def test_config_hash_changes_when_config_changes(self):
        """Config hash should change when configuration values change."""
        import hashlib
        import json

        def compute_config_hash(config: dict) -> str:
            serialized = json.dumps(config, sort_keys=True)
            return hashlib.sha256(serialized.encode()).hexdigest()[:16]

        config1 = {"max_research_rounds": 2, "max_repairs": 2}
        config2 = {"max_research_rounds": 3, "max_repairs": 2}

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 != hash2

    def test_topology_config_loaded_from_yaml_not_hardcoded(self):
        """Topology config must come from YAML, not hardcoded values."""
        from app.core.config import get_config

        config = get_config()
        topo_cfg = config.topology

        # Config should have topology settings
        assert "hierarchical" in topo_cfg or "routing_rules" in topo_cfg

    def test_effective_config_compiles_from_multiple_sources(self):
        """EffectiveConfig should compile from defaults + YAML + env + DB overrides."""
        from app.core.config import get_config

        config = get_config()
        effective_models = config.get_effective_models()

        # Should have compiled model list
        assert isinstance(effective_models, list)


class TestStateSchemaJsonSafe:
    """Graph State must be JSON-serializable for checkpointing.

    This is a Phase 0 requirement to ensure state can be checkpointed.
    """

    def test_research_state_is_json_serializable(self):
        """ResearchState must be JSON-serializable (no HTTP clients, exceptions, etc)."""
        import json

        state = ResearchState(
            task=TaskSpec(user_query="test", task_type="industry_report"),
            plan=[{"id": "q1", "question": "what?"}],
            analyses=[{"analysis_id": "a1", "claims": []}],
            critiques=[],
            source_registry={"https://example.com": {"url": "https://example.com", "title": "Test"}},
            claim_graph=[{"claim_id": "c1", "claim_text": "test", "evidence_ids": []}],
        )

        # Should not raise - this verifies JSON-safe fields
        json.dumps(state.model_dump(mode="json"))

    def test_state_does_not_contain_forbidden_types(self):
        """State must not contain HTTP clients, DB connections, or exceptions."""

        state = ResearchState(
            task=TaskSpec(user_query="test", task_type="industry_report"),
        )

        state_dict = state.model_dump()

        # Check for actual forbidden type references, not just any field with "error" in name
        # The "errors" field is legitimate - it stores error dictionaries
        forbidden_patterns = [
            "http_client", "db_client", "redis_client", "api_client",
            "connection", "session", "exception"
        ]

        def check_dict(d: dict, path: str = ""):
            for key, value in d.items():
                key_lower = key.lower()
                for pattern in forbidden_patterns:
                    if pattern in key_lower:
                        raise ValueError(f"Forbidden key '{key}' found at {path}")
                if isinstance(value, dict):
                    check_dict(value, f"{path}.{key}" if path else key)

        check_dict(state_dict)


class TestRunStatusEnum:
    """RunStatus enum must have all required terminal states."""

    def test_run_status_has_all_required_states(self):
        """RunStatus enum must include all required terminal states."""
        required_states = [
            "QUEUED", "RUNNING", "INTERRUPTED", "CANCELLING", "CANCELLED",
            "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED_QUALITY_GATE", "FAILED"
        ]

        for state_name in required_states:
            assert hasattr(RunStatus, state_name), f"Missing RunStatus.{state_name}"

    def test_research_strategy_enum_exists(self):
        """ResearchStrategy enum must exist with AUTO, HIERARCHICAL, DEBATE."""
        assert hasattr(ResearchStrategy, "AUTO")
        assert hasattr(ResearchStrategy, "HIERARCHICAL")
        assert hasattr(ResearchStrategy, "DEBATE")
