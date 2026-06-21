# Phase 5: Debate Graph

## Overview

Phase 5 implements the debate research strategy graph for open questions and strategy decisions. Unlike the hierarchical graph, the debate graph explores multiple hypotheses from different positions (support/oppose/alternative) and synthesizes them into a unified analysis.

## Components

### DebateState

TypedDict with debate-specific fields:

```python
class DebateState(TypedDict, total=False):
    # Root state
    run_id: str
    query: str
    task_type: str
    config_snapshot_id: str

    # Hypotheses
    hypotheses: list[str]
    current_hypothesis_index: int
    max_hypotheses: int

    # Debate branches
    debate_positions: dict[str, str]      # branch_id -> position
    debate_results: dict[str, dict]       # branch_id -> result
    completed_branch_ids: list[str]
    failed_branch_ids: list[str]

    # Evidence
    evidence_ids: list[str]

    # Cross-examination
    cross_examine_findings: list[dict]
    cross_examine_revision_id: str | None

    # Synthesis
    synthesis_id: str | None
    synthesis_revisions: list[str]
    claim_graph: list[dict]

    # Report
    report_revision_id: str | None
    report_revisions: list[str]

    # Validation & Repair
    validation_result: dict | None
    validation_decision: str | None
    repair_instructions: list[str]
    repair_count: int
    max_repairs: int

    # Terminal
    status: str
    terminal_reason: str | None
    warnings: list[str]
    errors: list[str]
```

### Nodes

#### generate_hypotheses_node
Generates 3 hypotheses from the query:
- Hypothesis A: Query is strongly supported
- Hypothesis B: Query is not supported
- Hypothesis C: Query requires nuance/alternative view

#### dispatch_debate_branches_node
Creates debate branches for each hypothesis with positions:
- `support-{index}` - SUPPORT position
- `oppose-{index}` - OPPOSE position
- `alternative-{index}` - ALTERNATIVE position (every other hypothesis)

#### join_debate_node
Collects evidence from all branch results and marks branches as completed.

#### cross_examine_node
Identifies conflicts between positions:
- Compares support vs oppose evidence counts
- Detects conflicts when both positions have evidence
- Produces consensus finding when no conflict detected

#### synthesize_node
Builds claim graph from debate results:
```python
claim_graph = [
    {
        "branch_id": branch_id,
        "position": position,  # support/oppose/alternative
        "evidence_count": len(evidence_ids),
        "status": result_status,
    }
]
```

#### write_report_node
Writes report from synthesis (uses authoritative synthesis_id).

#### validate_report_node
Validates report quality with score and decision.

#### validation_router
Routes based on validation decision:
- `pass` -> finalize_debate
- `repair` (under max) -> repair_report -> write_report
- `repair` (max reached) -> quality_gate_failed

#### repair_report_node
Increments repair count and adds repair instructions.

#### quality_gate_failed_node
Terminal state with `FAILED_QUALITY_GATE` status.

#### finalize_debate_node
Terminal state with `COMPLETED` status.

### DebateGraphBuilder

```python
from app.graphs.debate import DebateGraphBuilder

builder = DebateGraphBuilder(
    model_gateway=model_gateway,
    search_gateway=search_gateway,
    document_fetcher=document_fetcher,
    artifact_store=artifact_store,
)

result = await builder.run(initial_state)
```

## Flow

```
generate_hypotheses
    |
dispatch_debate_branches
    |
debate_branch (fan-out: support/oppose/alternative per hypothesis)
    |
join_debate
    |
cross_examine
    |
synthesize
    |
write_report
    |
validate_report
    |
validation_router
    |-- pass --> finalize_debate (terminal)
    |-- repair --> repair_report --> write_report (loop)
    |-- max repairs --> quality_gate_failed (terminal)
```

## Key Design Decisions

1. **DebatePosition Enum** - All position references use `DebatePosition.SUPPORT/OPPOSE/ALTERNATIVE`
2. **Hypothesis-based branching** - Each hypothesis gets support and oppose branches; alternative for variety
3. **Conflict detection** - Cross-examination explicitly compares support vs oppose evidence
4. **Claim graph** - Synthesis produces structured claim graph with position metadata
5. **Quality gate** - Same terminal state pattern as hierarchical graph

## Testing

16 tests in `test_phase5_debate.py`:

- `TestDebateHappyPath` (4 tests) - Complete flow, hypotheses, evidence, synthesis
- `TestDebatePositions` (2 tests) - Enum usage, all three positions present
- `TestCrossExamination` (2 tests) - Conflict detection, revision ID
- `TestSynthesis` (2 tests) - Claim graph positions, evidence counts
- `TestQualityGate` (4 tests) - Router pass/repair/max repairs, failure node
- `TestStateJsonSafe` (2 tests) - JSON serialization, forbidden types

## Differences from Hierarchical Graph

| Aspect | Hierarchical | Debate |
|--------|-------------|--------|
| Entry | prepare_research | generate_hypotheses |
| Branching | Wave-based subtasks | Position-based per hypothesis |
| Analysis | Single authoritative analysis | Synthesis from multiple positions |
| Critique | Internal critique loop | Cross-examination between positions |
| Claim graph | From single analysis | From debate results with positions |
| Target tasks | Industry reports, company analysis | Open questions, strategy decisions |

## Migration Status

- [x] DebateState with TypedDict and reducers
- [x] All debate nodes (generate, dispatch, join, cross_examine, synthesize, write, validate, repair, finalize)
- [x] DebateGraphBuilder with execution engine
- [x] DebatePosition enum integration
- [x] Claim graph with position metadata
- [x] Quality gate terminal states
- [x] All 16 Phase 5 tests passing
