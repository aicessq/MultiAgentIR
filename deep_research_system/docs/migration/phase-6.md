# Phase 6: Frontend Migration

## Overview

Phase 6 bridges the LangGraph backend event system to the frontend via SSE streaming. It provides:
- SSE formatting for ResearchEvents
- Progress tracking for both topologies
- Stage labeling in Chinese
- Event replay and live streaming

## Components

### SSEFormatter

Formats various event types into SSE-compatible strings:

```python
from app.frontend.streaming import SSEFormatter
from app.infrastructure.events.publisher import ResearchEvent, EventType

# Format a ResearchEvent
event = ResearchEvent(
    event_id="evt-1",
    sequence=1,
    run_id="run-1",
    thread_id="run-1",
    type=EventType.NODE_STARTED,
    node="search",
)
sse = SSEFormatter.format_event(event)
# Output: "event: node_started\nid: 1\ndata: {...}\n\n"

# Format progress update
sse = SSEFormatter.format_progress(50, "search", "run-1")

# Format node state change
sse = SSEFormatter.format_node_state("search", "running", "run-1")

# Format completion
sse = SSEFormatter.format_done("run-1", result={"report": {}})

# Format error
sse = SSEFormatter.format_error("Something failed", "run-1")

# Format cancellation
sse = SSEFormatter.format_cancelled("run-1")

# Keepalive ping
sse = SSEFormatter.keepalive()
```

### ProgressTracker

Maps LangGraph nodes to progress percentages and Chinese stage labels:

```python
from app.frontend.progress import ProgressTracker
from app.domain.enums import ResearchStrategy

# Hierarchical topology
tracker = ProgressTracker.for_topology(ResearchStrategy.HIERARCHICAL.value)
info = tracker.get_progress_info("write_report", "running")
# {
#     "progress": 70,
#     "stage": "write_report",
#     "stage_label": "撰写报告",
#     "topology": "hierarchical"
# }

# Debate topology
tracker = ProgressTracker.for_topology(ResearchStrategy.DEBATE.value)
info = tracker.get_progress_info("cross_examine", "running")
# {
#     "progress": 45,
#     "stage": "cross_examine",
#     "stage_label": "交叉检验",
#     "topology": "debate"
# }
```

**Progress Mappings:**

| Hierarchical Node | Progress | Debate Node | Progress |
|-------------------|----------|-------------|----------|
| prepare_research | 5 | generate_hypotheses | 5 |
| dispatch_research_wave | 10 | dispatch_debate_branches | 10 |
| research_branch | 20 | debate_branch | 25 |
| join_research | 30 | join_debate | 35 |
| build_analysis | 40 | cross_examine | 45 |
| critique | 50 | synthesize | 60 |
| generate_followups | 55 | write_report | 75 |
| write_report | 70 | validate_report | 85 |
| validate_report | 85 | repair_report | 90 |
| repair_report | 90 | finalize_debate | 100 |
| finalize_hierarchical | 100 | quality_gate_failed | 100 |

**Dynamic Labels:**
- Debate branches: `support-0` -> "辩论-支持 #0"
- Subtask agents: `searcher_sq_1` -> "搜索中 #1"
- Repair writer: `repair_writer_1` -> "修复写作中 #1"

### ResearchRunStreamer

High-level streamer for research runs:

```python
from app.frontend.streaming import ResearchRunStreamer
from app.infrastructure.events.publisher import EventPublisher

streamer = ResearchRunStreamer(event_publisher)

async for sse in streamer.stream_run(run_id, after_sequence=0):
    # Yield to FastAPI StreamingResponse
    yield sse
```

### EventStreamConsumer

Low-level consumer with keepalive support:

```python
from app.frontend.streaming import EventStreamConsumer

consumer = EventStreamConsumer(event_publisher, run_id)
async for sse in consumer.stream():
    yield sse
```

## Frontend Integration

### Existing Frontend (Vue 3 + Pinia)

The existing frontend already supports:
- SSE streaming via `EventSource`
- Progress bar with stage labels
- Agent detail panel
- Activity log
- Report viewer
- Cancellation

### Event Type Mapping

| Backend EventType | Frontend Event Type | Handler |
|-------------------|---------------------|---------|
| RUN_STARTED | start | Initialize run |
| NODE_STARTED | stage_start | Set node state to "running" |
| NODE_COMPLETED | stage_complete | Set node state to "completed" |
| RUN_COMPLETED | done | Mark run complete |
| RUN_FAILED | error | Show error |
| RUN_CANCELLED | cancelled | Mark cancelled |
| REPORT_COMPLETED | report_update | Update report |
| QUALITY_GATE_FAILED | quality_gate_failed | Show warning |

### API Endpoint

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

@router.get("/research/{run_id}/stream")
async def stream_research(run_id: str):
    streamer = ResearchRunStreamer(event_publisher)
    
    async def event_generator():
        async for sse in streamer.stream_run(run_id):
            yield sse
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

## Testing

19 tests in `test_phase6_frontend.py`:

- `TestSSEFormatter` (7 tests) - Event, progress, node_state, done, error, cancelled, keepalive
- `TestProgressTracker` (9 tests) - Hierarchical/debate mapping, labels, dynamic branches, terminal states
- `TestResearchRunStreamer` (2 tests) - Replay events, done event
- `TestEventJsonSafety` (2 tests) - to_sse JSON, format fields

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ ResearchView│  │ ProgressBar │  │ DetailPanel │         │
│  └──────┬──────┘  └─────────────┘  └─────────────┘         │
│         │                                                    │
│  ┌──────┴──────┐                                            │
│  │ research.ts │ (Pinia store)                              │
│  │  - SSE via EventSource                                   │
│  │  - Event parsing                                         │
│  │  - State management                                      │
│  └──────┬──────┘                                            │
└─────────┼────────────────────────────────────────────────────┘
          │ SSE
┌─────────┼────────────────────────────────────────────────────┐
│  ┌──────┴──────┐                                            │
│  │  FastAPI    │ /api/research/{run_id}/stream              │
│  │   Router    │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│  ┌──────┴──────┐                                            │
│  │ResearchRunStreamer│                                       │
│  │  - Replay events │                                        │
│  │  - Live streaming│                                        │
│  └──────┬──────┘                                            │
│         │                                                    │
│  ┌──────┴──────┐                                            │
│  │EventPublisher│                                            │
│  │  - Redis Streams                                          │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **SSEFormatter** - Centralized formatting for all SSE output
2. **ProgressTracker** - Topology-aware progress mapping with Chinese labels
3. **Event replay first** - Stream historical events before live events
4. **Keepalive pings** - Prevent connection timeout during long runs
5. **Backward compatible** - Existing frontend events still work

## Migration Status

- [x] SSEFormatter for all event types
- [x] ProgressTracker with topology-aware mappings
- [x] ResearchRunStreamer for event replay
- [x] EventStreamConsumer with keepalive
- [x] Chinese stage labels for all nodes
- [x] Dynamic labels for debate branches
- [x] All 19 Phase 6 tests passing
