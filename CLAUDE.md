# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent deep research system. Backend: Python 3.11+ / FastAPI. Frontend: Vue 3 / TypeScript / Vite / Element Plus. The system runs parallel AI agents (planner, searcher, reader, analyzer, critic, writer, validator) orchestrated through two topology modes (hierarchical, debate) to produce structured research reports with evidence-backed claims.

## Commands

### Backend (run from `deep_research_system/`)
```bash
# Start dev server
python main.py
# or
uvicorn main:app --reload --port 8000

# Run all tests
python -m pytest tests/ -v

# Run single test file
python -m pytest tests/test_report_validator.py -v

# Check Python syntax (no import dependencies needed)
python -c "import ast; ast.parse(open('app/topology/hierarchical.py').read())"
```

### Frontend (run from `deep_research_system/frontend/`)
```bash
npm run dev          # Vite dev server
npm run build        # vue-tsc + vite build
npx vue-tsc --noEmit # Type-check only
```

## Architecture

### Backend Layers

**API** (`app/api/`) — FastAPI routes. `routes_research.py` has POST `/research` (create task), GET `/research/{id}/stream` (SSE), GET `/research/{id}` (poll). SSE streams all agent events to frontend in real-time.

**Topology** (`app/topology/`) — Orchestrator layer. Two modes:
- `hierarchical.py` — Planner → parallel Searcher/Reader → Analyzer → Critic → (optional supplementary search loop) → Writer → Validator → (optional repair loop). Each sub-question gets its own searcher/reader instance via `asyncio.gather`.
- `debate.py` — Planner → parallel debate branches (pro/con/neutral) → Critic → Synthesizer → Writer → Validator → repair loop.
- `router.py` — Selects topology based on `task_type`.
- `base.py` — `BaseTopology.emit()` handles both sync/async event callbacks.

**Agents** (`app/agents/`) — Each agent extends `BaseAgent`. Key pattern: `BaseAgent.run()` selects model → streams LLM response token-by-token → parses JSON output → emits events. Agents declare `TaskRequirement` (model slot, capabilities, cost tier) for the model router.
- `_wrap_agent_name(on_event, name)` in `hierarchical.py` — wraps event callback to rename agent events for subtask nodes (e.g., `searcher_sq_1`) and composite stages (`supplementary_search`, `repair_writer`).

**Model Pool** (`app/model_pool/`) — `ModelRegistry` holds model configs. `FallbackRouter` selects models by capability/cost/latency requirements. `APIKeyPool` manages API keys. `LLMClient` handles streaming calls with retry.

**Prompts** (`prompts/`) — Jinja2 templates per agent. `app/prompts/loader.py` loads from disk, `renderer.py` renders with context. Templates are in `prompts/{agent}/` directories.

**Validators** (`app/validators/report_validator.py`) — Deterministic pre-check: placeholder detection, claim_id existence, source URL validation, risk_register completeness, as_of_date conflicts. Runs before LLM validator.

**Services** (`app/services/`) — `ResearchService` manages task lifecycle, SSE pub/sub, caching. `SearchService` wraps Tavily API with LLM-simulated fallback.

### Frontend Layers

**Store** (`stores/research.ts`) — Pinia store. Manages SSE connection, event routing, token buffering (50ms flush), node states, agent details. Key events: `stage_start`/`stage_complete` → node state, `agent_stream_token` → buffered display, `report_update` → intermediate report push, `done` → final result.

**Views** (`views/ResearchView.vue`) — Main page. Wires store to components. Computes `debateBranches`, `hasSupplementarySearch` from `nodeStates`.

**Research Components** (`components/research/`):
- `TopologyGraph.vue` — VueFlow canvas. Nodes are `ref` + `watch` (not computed) to preserve drag positions. Dynamically injects subtask nodes (`searcher_sq_*`, `reader_sq_*`) with collision-avoidant positioning.
- `AgentNode.vue` — Renders node with status color, streaming activity text.
- `DetailPanel.vue` — Structured output per agent type (planner sub-questions, searcher sources, reader evidence, etc.). Matches agent names including subtask patterns.
- `ReportViewer.vue` — Renders final report: key_claims, risk_register, as_of_date, uncertainties.
- `ProgressBar.vue` — Stage progress with labels including subtask/repair agents.

**Export** (`utils/export.ts`) — Markdown, PDF (html2pdf), Word (docx) export with claim_ids, risk_register, as_of_date.

### Data Flow for a Research Task

1. Frontend POSTs `/research` → gets `task_id`
2. Frontend opens SSE to `/research/{id}/stream`
3. Backend `ResearchService._execute()` runs topology with `on_topology_event` callback
4. Each agent emits events via `BaseAgent._emit()` → topology `emit()` → SSE to frontend
5. Frontend store routes events: `stage_start/complete` → nodeStates, `agent_stream_token` → token buffer, `report_update` → result.report, `agent_output` → detail.output
6. After topology completes, backend emits `done` event with `{report, metrics, audit_trail}`
7. Frontend renders report via ReportViewer, enables export

### Key Patterns

- **Parallel sub-tasks**: Topology creates separate agent instances per sub-question, runs via `asyncio.gather`, emits events with subtask-specific agent names (`searcher_sq_1`)
- **Event wrapping**: `_wrap_agent_name()` renames agent events for subtask/composite nodes without affecting topology-level `stage_start/stage_complete`
- **Repair loop**: Writer → Validator → if score < 85, re-run writer with `repair_context` (validation issues). Max 2 attempts. Validator runs with `on_event=None` during repair to avoid overwriting repair_writer node state.
- **Supplementary search loop**: Critic → if `needs_more_research`, run searcher with critic's suggested queries → re-analyze → re-critic. Max 1 loop.
- **Token streaming**: LLM streams tokens → `agent_stream_token` events → frontend buffers per agent → flushes every 50ms → updates node activity text
- **Deterministic validation**: `report_validator.py` runs code-level checks (no LLM) before the LLM validator. Fails fast on high-severity issues.

### Config Files (`config/`)
- `app.yaml` — App settings, cost estimates
- `models.yaml` — Model registry (name, endpoint, capabilities, rate limits)
- `agents.yaml` — Agent-specific configs
- `topology.yaml` — Topology settings (max sub-questions, repair loops, research loops)

### State Schema (`app/schemas/state.py`)
`ResearchState` is the central state object passed through all agents. Key fields: `task`, `plan`, `sub_results`, `analyses`, `critiques`, `claim_graph`, `claim_audit`, `source_registry`, `final_report`, `repair_context`, `debate_results`.

## Conventions

- All agent prompts are Jinja2 templates in `prompts/{agent}/`, versioned by filename (e.g., `v3_hypothesis.zh.j2`)
- Agent output parsing: `BaseAgent._parse_output()` extracts first JSON object from LLM response (finds `{`...`}`)
- Frontend agent names must match backend: `planner`, `searcher`, `reader`, `analyzer`, `critic`, `writer`, `validator`, `synthesizer`, `supplementary_search`, `repair_writer`, `searcher_sq_{id}`, `reader_sq_{id}`, `h_{index}`
- SSE event types: `stage_start`, `stage_complete`, `agent_model_selected`, `agent_thinking`, `agent_output`, `agent_stream_token`, `subtask_complete`, `report_update`, `done`, `cancelled`, `error`
