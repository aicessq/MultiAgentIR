"""SSE Streaming for LangGraph events.

Converts ResearchEvent stream to SSE format for frontend consumption.
Supports:
- Real-time progress updates
- Node state transitions
- Agent detail streaming
- Report updates
- Cancellation
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from app.infrastructure.events.publisher import EventPublisher, EventType, ResearchEvent

logger = logging.getLogger(__name__)


class SSEFormatter:
    """Formats ResearchEvents into SSE-compatible dicts."""

    @staticmethod
    def format_event(event: ResearchEvent) -> str:
        """Format a ResearchEvent as SSE string."""
        sse_data = event.to_sse()
        lines = [
            f"event: {sse_data['event']}",
            f"id: {sse_data['id']}",
            f"data: {sse_data['data']}",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_progress(progress: int, stage: str, run_id: str) -> str:
        """Format a progress update as SSE."""
        data = json.dumps({
            "type": "progress",
            "progress": progress,
            "stage": stage,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: progress\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_node_state(node: str, state: str, run_id: str) -> str:
        """Format a node state change as SSE."""
        data = json.dumps({
            "type": "node_state",
            "node": node,
            "state": state,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: node_state\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_agent_detail(agent: str, detail: dict, run_id: str) -> str:
        """Format agent detail update as SSE."""
        data = json.dumps({
            "type": "agent_detail",
            "agent": agent,
            "detail": detail,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: agent_detail\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_report_update(report: dict, run_id: str) -> str:
        """Format report update as SSE."""
        data = json.dumps({
            "type": "report_update",
            "report": report,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: report_update\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_done(run_id: str, result: dict | None = None) -> str:
        """Format completion event as SSE."""
        data = json.dumps({
            "type": "done",
            "run_id": run_id,
            "result": result,
        }, ensure_ascii=False)
        return f"event: done\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_error(error: str, run_id: str) -> str:
        """Format error event as SSE."""
        data = json.dumps({
            "type": "error",
            "error": error,
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: error\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def format_cancelled(run_id: str) -> str:
        """Format cancellation event as SSE."""
        data = json.dumps({
            "type": "cancelled",
            "run_id": run_id,
        }, ensure_ascii=False)
        return f"event: cancelled\nid: 0\ndata: {data}\n\n"

    @staticmethod
    def keepalive() -> str:
        """Format keepalive ping."""
        return ": keepalive\n\n"


class EventStreamConsumer:
    """Consumes ResearchEvents and produces SSE-formatted strings.

    Usage:
        consumer = EventStreamConsumer(event_publisher, run_id)
        async for sse_string in consumer.stream():
            yield sse_string
    """

    def __init__(
        self,
        event_publisher: EventPublisher,
        run_id: str,
        keepalive_interval: float = 30.0,
    ) -> None:
        self._publisher = event_publisher
        self._run_id = run_id
        self._keepalive_interval = keepalive_interval
        self._formatter = SSEFormatter()
        self._last_sequence = 0

    async def stream(self) -> AsyncIterator[str]:
        """Stream SSE-formatted events."""
        try:
            async for event in self._publisher.replay(self._run_id, after_sequence=0):
                self._last_sequence = event.sequence
                yield self._formatter.format_event(event)

            # After replay, stream live events
            while True:
                try:
                    # Wait for new events with timeout
                    await asyncio.wait_for(
                        self._wait_for_next_event(),
                        timeout=self._keepalive_interval,
                    )
                except asyncio.TimeoutError:
                    yield self._formatter.keepalive()

        except asyncio.CancelledError:
            logger.info(f"Event stream cancelled for run {self._run_id}")
            raise

    async def _wait_for_next_event(self) -> None:
        """Wait for next event (placeholder for live streaming)."""
        # In production, this would subscribe to Redis pub/sub
        await asyncio.sleep(0.1)

    async def stream_with_progress(
        self,
        progress_callback: Any | None = None,
    ) -> AsyncIterator[str]:
        """Stream with progress tracking."""
        async for sse in self.stream():
            yield sse


class ResearchRunStreamer:
    """High-level streamer for research runs.

    Combines event replay, live streaming, and progress tracking.
    """

    def __init__(
        self,
        event_publisher: EventPublisher,
    ) -> None:
        self._publisher = event_publisher
        self._formatter = SSEFormatter()

    async def stream_run(
        self,
        run_id: str,
        after_sequence: int = 0,
    ) -> AsyncIterator[str]:
        """Stream all events for a research run.

        Usage:
            async for sse in streamer.stream_run(run_id):
                yield sse
        """
        # Replay historical events
        async for event in self._publisher.replay(run_id, after_sequence):
            yield self._formatter.format_event(event)

        # Send done event if run is complete
        yield self._formatter.format_done(run_id)
