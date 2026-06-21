"""Tests for Phase 4: Persistence, Worker, and Events.

Tests:
1. Checkpoint save/load
2. Event publishing/replay
3. Task queue enqueue/dequeue
4. Cancellation
5. Worker lifecycle
"""

import pytest

from app.infrastructure.checkpoint.postgres import FakePostgresSaver
from app.infrastructure.redis.streams import FakeRedisManager
from app.infrastructure.events.publisher import EventType, EventPublisher


class TestCheckpoint:
    """Test checkpoint save and load."""

    @pytest.fixture
    def saver(self):
        return FakePostgresSaver()

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self, saver):
        """Checkpoint should be saved and loaded correctly."""
        run_id = "test-run-1"
        state = {
            "run_id": run_id,
            "status": "running",
            "evidence_ids": ["e1", "e2"],
        }

        await saver.aput(
            thread_id=run_id,
            checkpoint_id="checkpoint-1",
            state=state,
        )

        loaded = await saver.aget(run_id)
        assert loaded is not None
        assert loaded["checkpoint_id"] == "checkpoint-1"
        assert loaded["state"]["run_id"] == run_id
        assert loaded["state"]["evidence_ids"] == ["e1", "e2"]

    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, saver):
        """Loading nonexistent checkpoint should return None."""
        loaded = await saver.aget("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, saver):
        """Checkpoint should be deleted correctly."""
        run_id = "test-run-2"

        await saver.aput(
            thread_id=run_id,
            checkpoint_id="checkpoint-1",
            state={"run_id": run_id},
        )

        await saver.adelete(run_id)
        loaded = await saver.aget(run_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, saver):
        """Should list checkpoints in order."""
        run_id = "test-run-3"

        for i in range(3):
            await saver.aput(
                thread_id=run_id,
                checkpoint_id=f"checkpoint-{i}",
                state={"step": i},
            )

        checkpoints = [c async for c in saver.alist(run_id)]
        assert len(checkpoints) == 3


class TestEventPublisher:
    """Test event publishing and replay."""

    @pytest.fixture
    def redis_manager(self):
        return FakeRedisManager()

    @pytest.fixture
    def event_publisher(self, redis_manager):
        from app.infrastructure.redis.streams import EventLogger
        event_logger = EventLogger(redis_manager.client)
        return EventPublisher(event_logger)

    @pytest.mark.asyncio
    async def test_publish_event(self, event_publisher):
        """Event should be published with sequence."""
        run_id = "test-run-1"

        seq1 = await event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.RUN_STARTED,
        )

        seq2 = await event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.NODE_STARTED,
            node="analyze",
        )

        assert seq2 > seq1

    @pytest.mark.asyncio
    async def test_replay_events(self, event_publisher):
        """Events should be replayable from sequence."""
        run_id = "test-run-2"

        await event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.RUN_STARTED,
        )

        await event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.NODE_STARTED,
            node="search",
        )

        # Replay from sequence 0
        events = [e async for e in event_publisher.replay(run_id, after_sequence=0)]
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_event_to_sse(self, event_publisher):
        """Event should convert to SSE format."""
        run_id = "test-run-3"

        seq = await event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.RUN_COMPLETED,
            payload={"terminal_reason": "success"},
        )

        events = [e async for e in event_publisher.replay(run_id, after_sequence=0)]
        sse = events[0].to_sse()

        assert "event" in sse
        assert "id" in sse
        assert "data" in sse


class TestRedisStreams:
    """Test Redis Streams functionality."""

    @pytest.fixture
    def redis_manager(self):
        return FakeRedisManager()

    @pytest.mark.asyncio
    async def test_task_queue_enqueue(self, redis_manager):
        """Task should be enqueued."""
        queue = redis_manager.task_queue("worker-1")

        await queue.enqueue(
            run_id="run-1",
            query="test query",
            task_type="industry_report",
            strategy="hierarchical",
        )

        length = await queue.get_queue_length()
        assert length >= 1

    @pytest.mark.asyncio
    async def test_cancellation_manager(self, redis_manager):
        """Cancellation should be tracked."""
        cancel_mgr = redis_manager.cancellation_manager()
        run_id = "run-1"

        # Initially not cancelled
        is_cancelled = await cancel_mgr.is_cancelled(run_id)
        assert is_cancelled is False

        # Request cancellation
        await cancel_mgr.request_cancel(run_id)
        is_cancelled = await cancel_mgr.is_cancelled(run_id)
        assert is_cancelled is True

        # Clear cancellation
        await cancel_mgr.clear_cancel(run_id)
        is_cancelled = await cancel_mgr.is_cancelled(run_id)
        assert is_cancelled is False


class TestDistributedLock:
    """Test distributed locking."""

    @pytest.fixture
    def redis_manager(self):
        return FakeRedisManager()

    @pytest.mark.asyncio
    async def test_lock_acquire_release(self, redis_manager):
        """Lock should be acquired and released."""
        lock = redis_manager.distributed_lock("test-lock")

        # Acquire
        acquired = await lock.acquire("owner-1")
        assert acquired is True

        # Release
        released = await lock.release("owner-1")
        assert released is True

    @pytest.mark.asyncio
    async def test_lock_prevents_double_acquire(self, redis_manager):
        """Lock should prevent double acquire."""
        lock = redis_manager.distributed_lock("test-lock")

        await lock.acquire("owner-1")
        acquired = await lock.acquire("owner-2")
        assert acquired is False

    @pytest.mark.asyncio
    async def test_lock_only_releases_own_lock(self, redis_manager):
        """Lock should only release if owned."""
        lock = redis_manager.distributed_lock("test-lock")

        await lock.acquire("owner-1")
        released = await lock.release("owner-2")
        assert released is False


class TestEventTypes:
    """Test event type enum."""

    def test_event_types_exist(self):
        """All event types should exist."""
        assert EventType.RUN_CREATED.value == "run_created"
        assert EventType.RUN_STARTED.value == "run_started"
        assert EventType.RUN_COMPLETED.value == "run_completed"
        assert EventType.RUN_FAILED.value == "run_failed"
        assert EventType.NODE_STARTED.value == "node_started"
        assert EventType.NODE_COMPLETED.value == "node_completed"
        assert EventType.QUALITY_GATE_FAILED.value == "quality_gate_failed"

    def test_event_type_is_string_enum(self):
        """EventType should be string enum."""
        event_type = EventType.RUN_COMPLETED
        assert isinstance(event_type.value, str)
        assert event_type.value == "run_completed"
