# Phase 4: Persistence, Worker & Events

## Overview

Phase 4 implements persistence, worker lifecycle, and event infrastructure for the LangGraph-based research system.

## Components

### Checkpoint Persistence

#### AsyncPostgresSaver
PostgreSQL-based checkpointer for LangGraph state persistence.

```python
from app.infrastructure.checkpoint.postgres import AsyncPostgresSaver

saver = AsyncPostgresSaver(session_factory)
graph = builder.compile(checkpointer=saver)
```

**Interface:**
- `aget(thread_id)` - Get latest checkpoint
- `alist(thread_id, limit)` - List checkpoints (newest first)
- `aput(thread_id, checkpoint_id, state, parent_checkpoint_id, metadata)` - Save checkpoint
- `adelete(thread_id)` - Delete all checkpoints for thread
- `aget_next_version(thread_id, checkpoint_id)` - Generate next version ID

#### CheckpointRecord Model
```python
class CheckpointRecord(Base):
    thread_id: str          # Primary key (run_id)
    checkpoint_id: str      # Primary key
    parent_checkpoint_id: str | None
    state: JSON
    checkpoint_metadata: JSON
    created_at: datetime
```

### Event System

#### EventType Enum
All event types for the research system:

**Run Lifecycle:**
- `RUN_CREATED`, `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`, `RUN_INTERRUPTED`

**Graph Events:**
- `NODE_STARTED`, `NODE_COMPLETED`, `NODE_FAILED`, `PHASE_CHANGED`

**Research Events:**
- `SEARCH_STARTED`, `SEARCH_COMPLETED`, `FETCH_STARTED`, `FETCH_COMPLETED`, `EVIDENCE_EXTRACTED`

**Analysis Events:**
- `ANALYSIS_STARTED`, `ANALYSIS_COMPLETED`, `CRITIQUE_STARTED`, `CRITIQUE_COMPLETED`

**Report Events:**
- `REPORT_STARTED`, `REPORT_COMPLETED`, `VALIDATION_STARTED`, `VALIDATION_COMPLETED`, `REPAIR_STARTED`

**Quality Gate:**
- `QUALITY_GATE_PASSED`, `QUALITY_GATE_FAILED`

**Usage:**
- `USAGE_UPDATED`, `BUDGET_WARNING`, `BUDGET_EXCEEDED`

**Artifact:**
- `ARTIFACT_CREATED`, `ARTIFACT_UPDATED`

#### ResearchEvent Model
```python
class ResearchEvent(BaseModel):
    event_id: str
    sequence: int
    schema_version: str = "v1"
    run_id: str
    thread_id: str
    type: EventType
    node: str | None = None
    namespace: list[str] = []
    attempt: int | None = None
    timestamp: datetime
    payload: dict = {}
```

#### EventPublisher
Publishes events to Redis Streams.

```python
from app.infrastructure.events.publisher import EventPublisher, EventType

publisher = EventPublisher(event_logger)
seq = await publisher.publish(
    run_id=run_id,
    thread_id=thread_id,
    event_type=EventType.NODE_STARTED,
    node="search",
)

# Replay events
async for event in publisher.replay(run_id, after_sequence=0):
    print(event)
```

#### EventLogger
Redis Stream-based event logger with replay support.

**Key patterns:**
- `research:events:{run_id}` - Event stream per run

### Redis Streams

#### TaskQueue
Redis-based task queue using Streams.

```python
from app.infrastructure.redis.streams import TaskQueue

queue = TaskQueue(redis_client, worker_id="worker-1")
await queue.enqueue(run_id="run-1", query="...", task_type="industry_report", strategy="hierarchical")
task = await queue.dequeue()
await queue.acknowledge(task["_message_id"])
```

#### CancellationManager
Distributed cancellation using Redis.

```python
from app.infrastructure.redis.streams import CancellationManager

cancel_mgr = CancellationManager(redis_client)
await cancel_mgr.request_cancel(run_id)
is_cancelled = await cancel_mgr.is_cancelled(run_id)
await cancel_mgr.clear_cancel(run_id)
```

#### DistributedLock
Redis-based distributed lock with TTL.

```python
from app.infrastructure.redis.streams import DistributedLock

lock = DistributedLock(redis_client, lock_key="run-lock", ttl_seconds=60)
acquired = await lock.acquire(owner_id="worker-1")
released = await lock.release(owner_id="worker-1")
```

**Key patterns:**
- `research:queue:{worker_id}` - Task queue per worker
- `research:locks:{run_id}` - Distributed locks
- `research:cancel:{run_id}` - Cancel signals
- `research:state:{run_id}` - State storage

### Worker

#### Worker
Single worker process for executing research tasks.

```python
from app.worker.process import Worker

worker = Worker(
    worker_id="worker-1",
    research_graph_builder=builder,
    event_publisher=publisher,
)
await worker.start()
```

**Features:**
- Graceful shutdown on SIGINT/SIGTERM
- Cancellation checking during execution
- Checkpoint saving on cancellation
- Event publishing for run lifecycle

#### WorkerPool
Horizontal scaling of workers.

```python
from app.worker.process import WorkerPool

pool = WorkerPool(
    research_graph_builder=builder,
    event_publisher=publisher,
    worker_count=4,
)
await pool.start()
```

### Database Schema

14 SQLAlchemy models for persistence:

1. **ResearchRun** - Run metadata and status
2. **ConfigSnapshot** - Configuration at run start
3. **ResearchArtifact** - Analysis, critique, report revisions
4. **Source** - Search sources
5. **Document** - Fetched documents
6. **Evidence** - Extracted evidence
7. **Claim** - Extracted claims
8. **AnalysisRevision** - Analysis versions
9. **CritiqueRevision** - Critique versions
10. **ReportRevision** - Report versions
11. **ValidationResult** - Validation outcomes
12. **ModelCallAudit** - API call logging

**Note:** `metadata` column renamed to `extra_metadata` to avoid SQLAlchemy reserved word conflict.

## Testing

14 tests in `test_phase4_persistence.py`:

- `TestCheckpoint` (4 tests) - Checkpoint save/load/delete/list
- `TestEventPublisher` (3 tests) - Publish/replay/SSE conversion
- `TestRedisStreams` (2 tests) - Task queue/cancellation
- `TestDistributedLock` (3 tests) - Lock acquire/release/prevention
- `TestEventTypes` (2 tests) - Enum validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WorkerPool                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ Worker1 │ │ Worker2 │ │ Worker3 │ │ Worker4 │            │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘            │
│       │           │           │           │                  │
│       └───────────┴───────────┴───────────┘                  │
│                         │                                     │
│                    LangGraph                                 │
│                         │                                     │
│              ┌──────────┴──────────┐                        │
│              │   Checkpointer      │                        │
│              │  (AsyncPostgresSaver)│                        │
│              └──────────┬──────────┘                        │
│                         │                                     │
│              ┌──────────┴──────────┐                        │
│              │   EventPublisher   │                        │
│              │  (Redis Streams)   │                        │
│              └────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **AsyncPostgresSaver** implements LangGraph checkpointer interface for seamless integration
2. **EventLogger** uses Redis Streams for event replay capability
3. **DistributedLock** uses Redis SET with NX for atomic lock acquisition
4. **CancellationManager** uses Redis SET with expiry for automatic cleanup
5. **Worker** publishes events for all run lifecycle transitions

## Migration Status

- [x] AsyncPostgresSaver with FakePostgresSaver for testing
- [x] EventPublisher with Redis Stream backend
- [x] TaskQueue, CancellationManager, DistributedLock
- [x] Worker and WorkerPool with graceful shutdown
- [x] Database schema with proper column naming
- [x] All 14 Phase 4 tests passing
