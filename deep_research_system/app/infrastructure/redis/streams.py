"""Redis Streams for task queue and event log.

Key patterns:
- research:queue:{worker_id} - Task queue per worker
- research:events:{run_id} - Event stream per run
- research:locks:{run_id} - Distributed locks
- research:cancel:{run_id} - Cancel signals
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator

import redis.asyncio as redis

from app.domain.enums import RunStatus

logger = logging.getLogger(__name__)


class RedisStreamKeys:
    """Redis key patterns."""

    QUEUE = "research:queue:{worker_id}"
    EVENTS = "research:events:{run_id}"
    LOCKS = "research:locks:{run_id}"
    CANCEL = "research:cancel:{run_id}"
    STATE = "research:state:{run_id}"


class TaskQueue:
    """Redis-based task queue using Streams.

    Each worker has its own stream-based queue.
    Tasks are distributed using XADD and XREADGROUP.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        worker_id: str,
        consumer_group: str = "workers",
    ) -> None:
        self._redis = redis_client
        self._worker_id = worker_id
        self._consumer_group = consumer_group
        self._queue_key = RedisStreamKeys.QUEUE.format(worker_id=worker_id)

    async def enqueue(
        self,
        run_id: str,
        query: str,
        task_type: str,
        strategy: str,
        priority: int = 0,
    ) -> None:
        """Add a task to the queue."""
        task_data = {
            "run_id": run_id,
            "query": query,
            "task_type": task_type,
            "strategy": strategy,
            "priority": str(priority),
            "enqueued_at": datetime.utcnow().isoformat(),
        }
        await self._redis.xadd(self._queue_key, task_data)
        logger.info(f"Enqueued task {run_id} to {self._queue_key}")

    async def dequeue(self, timeout_ms: int = 5000) -> dict | None:
        """Dequeue a task (blocking)."""
        # First, try to claim pending messages
        try:
            messages = await self._redis.xreadgroup(
                groupname=self._consumer_group,
                consumername=self._worker_id,
                streams={self._queue_key: ">"},
                count=1,
                block=timeout_ms,
            )
        except redis.ResponseError:
            # Consumer group doesn't exist, create it
            await self._redis.xgroup_create(
                self._queue_key, self._consumer_group, id="0", mkstream=True
            )
            messages = await self._redis.xreadgroup(
                groupname=self._consumer_group,
                consumername=self._worker_id,
                streams={self._queue_key: ">"},
                count=1,
                block=timeout_ms,
            )

        if messages:
            stream, entries = messages[0]
            if entries:
                message_id, data = entries[0]
                task = dict(data)
                task["_message_id"] = message_id
                return task

        return None

    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge a task was processed."""
        await self._redis.xack(self._queue_key, self._consumer_group, message_id)

    async def requeue(self, message_id: str, delay_ms: int = 0) -> None:
        """Requeue a failed task with optional delay."""
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        # Get original message and re-add to queue
        messages = await self._redis.xrange(
            self._queue_key, min=message_id, max=message_id
        )
        if messages:
            _, data = messages[0]
            await self._redis.xadd(self._queue_key, dict(data))

    async def get_queue_length(self) -> int:
        """Get approximate queue length."""
        info = await self._redis.xinfo_stream(self._queue_key)
        return info.get("length", 0)


class EventLogger:
    """Redis Stream-based event logger with replay support.

    Each run has its own stream for events.
    Supports:
    - Publishing events
    - Replaying events by sequence
    - Last-Event-ID based recovery
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        maxlen: int = 10000,
    ) -> None:
        self._redis = redis_client
        self._maxlen = maxlen

    async def publish(
        self,
        run_id: str,
        thread_id: str,
        event_type: str,
        node: str | None,
        namespace: list[str],
        attempt: int | None,
        payload: dict,
    ) -> int:
        """Publish an event to the run's stream.

        Returns the sequence number.
        """
        import uuid

        stream_key = RedisStreamKeys.EVENTS.format(run_id=run_id)

        event = {
            "event_id": str(uuid.uuid4()),
            "sequence": str(int(time.time() * 1000)),  # Millisecond timestamp as sequence
            "schema_version": "v1",
            "run_id": run_id,
            "thread_id": thread_id,
            "type": event_type,
            "node": node or "",
            "namespace": json.dumps(namespace),
            "attempt": str(attempt) if attempt is not None else "",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": json.dumps(payload),
        }

        # Use MAXLEN to bound stream size
        message_id = await self._redis.xadd(stream_key, event, maxlen=self._maxlen)

        # Parse sequence from message_id (format: timestamp-seqnum)
        sequence = int(message_id.split("-")[0])

        logger.debug(f"Published event {event_type} to {stream_key}, seq={sequence}")
        return sequence

    async def replay(
        self,
        run_id: str,
        after_sequence: int = 0,
        limit: int = 1000,
    ) -> AsyncIterator[dict]:
        """Replay events from a sequence number.

        Usage:
            async for event in event_logger.replay(run_id, after_sequence=100):
                print(event)
        """
        stream_key = RedisStreamKeys.EVENTS.format(run_id=run_id)

        # Query events after the sequence
        min_id = f"{after_sequence}-0"
        max_id = "+"

        messages = await self._redis.xrange(stream_key, min=min_id, max=max_id, count=limit)

        for message_id, data in messages:
            event = dict(data)
            event["_message_id"] = message_id

            # Parse JSON fields
            if event.get("namespace"):
                event["namespace"] = json.loads(event["namespace"])
            if event.get("payload"):
                event["payload"] = json.loads(event["payload"])

            yield event

    async def get_last_sequence(self, run_id: str) -> int:
        """Get the last event sequence for a run."""
        stream_key = RedisStreamKeys.EVENTS.format(run_id=run_id)

        messages = await self._redis.xrevrange(stream_key, "+", "-", count=1)
        if messages:
            message_id, _ = messages[0]
            return int(message_id.split("-")[0])
        return 0

    async def get_event_count(self, run_id: str) -> int:
        """Get event count for a run."""
        stream_key = RedisStreamKeys.EVENTS.format(run_id=run_id)
        try:
            info = await self._redis.xinfo_stream(stream_key)
            return info.get("length", 0)
        except redis.ResponseError:
            return 0


class CancellationManager:
    """Distributed cancellation manager using Redis."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def request_cancel(self, run_id: str) -> None:
        """Request cancellation of a run."""
        cancel_key = RedisStreamKeys.CANCEL.format(run_id=run_id)
        await self._redis.set(
            cancel_key,
            datetime.utcnow().isoformat(),
            ex=86400,  # Expire after 24 hours
        )
        logger.info(f"Cancellation requested for run {run_id}")

    async def is_cancelled(self, run_id: str) -> bool:
        """Check if cancellation was requested."""
        cancel_key = RedisStreamKeys.CANCEL.format(run_id=run_id)
        return await self._redis.exists(cancel_key) > 0

    async def clear_cancel(self, run_id: str) -> None:
        """Clear cancellation request."""
        cancel_key = RedisStreamKeys.CANCEL.format(run_id=run_id)
        await self._redis.delete(cancel_key)


class DistributedLock:
    """Distributed lock using Redis."""

    def __init__(
        self,
        redis_client: redis.Redis,
        lock_key: str,
        ttl_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._lock_key = lock_key
        self._ttl_seconds = ttl_seconds

    async def acquire(self, owner_id: str) -> bool:
        """Acquire the lock."""
        result = await self._redis.set(
            self._lock_key,
            owner_id,
            nx=True,
            ex=self._ttl_seconds,
        )
        return result is not None

    async def release(self, owner_id: str) -> bool:
        """Release the lock (only if we own it)."""
        current = await self._redis.get(self._lock_key)
        if current == owner_id:
            await self._redis.delete(self._lock_key)
            return True
        return False

    async def extend(self, owner_id: str, ttl_seconds: int | None = None) -> bool:
        """Extend the lock TTL."""
        current = await self._redis.get(self._lock_key)
        if current == owner_id:
            ttl = ttl_seconds or self._ttl_seconds
            await self._redis.expire(self._lock_key, ttl)
            return True
        return False


class RedisManager:
    """Manager for Redis connections and utilities."""

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        max_connections: int = 10,
    ) -> None:
        self._url = url
        self._max_connections = max_connections
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = redis.ConnectionPool.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return self._client

    def task_queue(self, worker_id: str) -> TaskQueue:
        """Create a task queue for a worker."""
        return TaskQueue(self.client, worker_id)

    def event_logger(self) -> EventLogger:
        """Create an event logger."""
        return EventLogger(self.client)

    def cancellation_manager(self) -> CancellationManager:
        """Create a cancellation manager."""
        return CancellationManager(self._client)

    def distributed_lock(self, lock_key: str, ttl: int = 60) -> DistributedLock:
        """Create a distributed lock."""
        return DistributedLock(self._client, lock_key, ttl)


class FakeRedisManager:
    """Fake Redis manager for testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    @property
    def client(self) -> "FakeRedisManager":
        return self

    def task_queue(self, worker_id: str) -> TaskQueue:
        """Create a task queue for a worker."""
        return TaskQueue(self, worker_id)

    def event_logger(self) -> EventLogger:
        """Create an event logger."""
        return EventLogger(self)

    def cancellation_manager(self) -> CancellationManager:
        """Create a cancellation manager."""
        return CancellationManager(self)

    def distributed_lock(self, lock_key: str, ttl: int = 60) -> DistributedLock:
        """Create a distributed lock."""
        return DistributedLock(self, lock_key, ttl)

    # Fake TaskQueue
    async def xadd(self, key: str, data: dict, **kwargs) -> str:
        if key not in self._data:
            self._data[key] = []
        seq = len(self._data[key])
        message_id = f"{int(time.time() * 1000)}-{seq}"
        self._data[key].append((message_id, data))
        return message_id

    async def xreadgroup(self, groupname, consumername, streams, count, block) -> list:
        return []

    async def xgroup_create(self, stream, group, id, mkstream) -> None:
        pass

    async def xack(self, stream, group, *ids) -> None:
        pass

    async def xrange(self, stream, min, max, count) -> list:
        return self._data.get(stream, [])

    async def xrevrange(self, stream, max, min, count) -> list:
        data = self._data.get(stream, [])
        return list(reversed(data))

    async def xinfo_stream(self, stream) -> dict:
        return {"length": len(self._data.get(stream, []))}

    # Fake general operations
    async def set(self, key: str, value: str, ex=None, nx=False) -> bool:
        if nx and key in self._data:
            return None
        self._data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)

    async def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    async def expire(self, key: str, seconds: int) -> None:
        pass
