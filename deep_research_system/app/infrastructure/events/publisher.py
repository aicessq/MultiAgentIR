"""Event types for the research system.

All events are published to Redis Streams and converted to SSE.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types."""

    # Run lifecycle
    RUN_CREATED = "run_created"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    RUN_INTERRUPTED = "run_interrupted"

    # Graph events
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    PHASE_CHANGED = "phase_changed"

    # Research events
    SEARCH_STARTED = "search_started"
    SEARCH_COMPLETED = "search_completed"
    FETCH_STARTED = "fetch_started"
    FETCH_COMPLETED = "fetch_completed"
    EVIDENCE_EXTRACTED = "evidence_extracted"

    # Analysis events
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    CRITIQUE_STARTED = "critique_started"
    CRITIQUE_COMPLETED = "critique_completed"

    # Report events
    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    REPAIR_STARTED = "repair_started"

    # Quality gate
    QUALITY_GATE_PASSED = "quality_gate_passed"
    QUALITY_GATE_FAILED = "quality_gate_failed"

    # Usage
    USAGE_UPDATED = "usage_updated"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"

    # Artifact
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_UPDATED = "artifact_updated"


class ResearchEvent(BaseModel):
    """Base event for all research events.

    Published to Redis Stream and converted to SSE.
    """

    event_id: str
    sequence: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    schema_version: str = "v1"
    run_id: str
    thread_id: str
    type: EventType
    node: str | None = None
    namespace: list[str] = Field(default_factory=list)
    attempt: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict = Field(default_factory=dict)

    def to_sse(self) -> dict:
        """Convert to Server-Sent Events format."""
        return {
            "event": self.type.value,
            "id": str(self.sequence),
            "data": self.model_dump_json(),
        }

    @classmethod
    def from_sse(cls, data: dict) -> ResearchEvent:
        """Create from SSE data."""
        event_data = data.get("data", {})
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
        return cls(**event_data)


class EventPublisher:
    """Publishes events to Redis Streams.

    Converts LangGraph events to ResearchEvents.
    """

    def __init__(self, event_logger: Any) -> None:
        self._event_logger = event_logger
        self._sequence: dict[str, int] = {}

    async def publish(
        self,
        run_id: str,
        thread_id: str,
        event_type: EventType,
        node: str | None = None,
        namespace: list[str] | None = None,
        attempt: int | None = None,
        payload: dict | None = None,
    ) -> int:
        """Publish an event.

        Returns the sequence number.
        """
        import uuid

        # Get next sequence for this run
        if run_id not in self._sequence:
            self._sequence[run_id] = await self._event_logger.get_last_sequence(run_id)

        self._sequence[run_id] += 1
        sequence = self._sequence[run_id]

        event = ResearchEvent(
            event_id=str(uuid.uuid4()),
            sequence=sequence,
            run_id=run_id,
            thread_id=thread_id,
            type=event_type,
            node=node,
            namespace=namespace or [],
            attempt=attempt,
            payload=payload or {},
        )

        await self._event_logger.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=event_type.value,
            node=node,
            namespace=namespace or [],
            attempt=attempt,
            payload=payload or {},
        )

        return sequence

    async def publish_node_started(
        self, run_id: str, thread_id: str, node: str, attempt: int | None = None
    ) -> int:
        """Publish node started event."""
        return await self.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=EventType.NODE_STARTED,
            node=node,
            attempt=attempt,
        )

    async def publish_node_completed(
        self, run_id: str, thread_id: str, node: str, payload: dict | None = None
    ) -> int:
        """Publish node completed event."""
        return await self.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=EventType.NODE_COMPLETED,
            node=node,
            payload=payload or {},
        )

    async def publish_run_completed(
        self, run_id: str, thread_id: str, payload: dict | None = None
    ) -> int:
        """Publish run completed event."""
        return await self.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=EventType.RUN_COMPLETED,
            payload=payload or {},
        )

    async def publish_run_failed(
        self, run_id: str, thread_id: str, error: str, payload: dict | None = None
    ) -> int:
        """Publish run failed event."""
        return await self.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=EventType.RUN_FAILED,
            payload={**(payload or {}), "error": error},
        )

    async def publish_quality_gate_failed(
        self, run_id: str, thread_id: str, score: float, issues: list[dict]
    ) -> int:
        """Publish quality gate failed event."""
        return await self.publish(
            run_id=run_id,
            thread_id=thread_id,
            event_type=EventType.QUALITY_GATE_FAILED,
            payload={"score": score, "issues": issues},
        )

    async def replay(
        self, run_id: str, after_sequence: int = 0
    ) -> AsyncIterator[ResearchEvent]:
        """Replay events from a sequence."""
        import json
        from typing import AsyncIterator

        async for raw_event in self._event_logger.replay(run_id, after_sequence):
            namespace = raw_event.get("namespace", [])
            if isinstance(namespace, str):
                namespace = json.loads(namespace)
            elif not isinstance(namespace, list):
                namespace = []

            payload = raw_event.get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload)

            yield ResearchEvent(
                event_id=raw_event["event_id"],
                sequence=int(raw_event["sequence"]),
                run_id=raw_event["run_id"],
                thread_id=raw_event["thread_id"],
                type=EventType(raw_event["type"]),
                node=raw_event.get("node") or None,
                namespace=namespace,
                attempt=int(raw_event["attempt"]) if raw_event.get("attempt") else None,
                payload=payload,
            )
