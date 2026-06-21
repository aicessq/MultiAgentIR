"""Tests for Phase 6: Frontend Integration.

Tests:
1. SSEFormatter formats events correctly
2. ProgressTracker maps nodes to progress
3. ProgressTracker handles both topologies
4. ProgressTracker stage labels
5. ResearchRunStreamer replays events
6. Event stream JSON safety
"""

import pytest

from app.domain.enums import ResearchStrategy
from app.frontend.progress import ProgressTracker
from app.frontend.streaming import SSEFormatter, ResearchRunStreamer
from app.infrastructure.events.publisher import EventType, ResearchEvent
from app.infrastructure.redis.streams import FakeRedisManager
from app.infrastructure.events.publisher import EventPublisher


class TestSSEFormatter:
    """Test SSE formatting."""

    def test_format_event(self):
        """Should format ResearchEvent as SSE string."""
        event = ResearchEvent(
            event_id="evt-1",
            sequence=1,
            run_id="run-1",
            thread_id="run-1",
            type=EventType.NODE_STARTED,
            node="search",
        )
        sse = SSEFormatter.format_event(event)
        assert "event: node_started" in sse
        assert "id: 1" in sse
        assert "data:" in sse

    def test_format_progress(self):
        """Should format progress as SSE."""
        sse = SSEFormatter.format_progress(50, "search", "run-1")
        assert "event: progress" in sse
        assert '"progress": 50' in sse
        assert '"stage": "search"' in sse

    def test_format_node_state(self):
        """Should format node state as SSE."""
        sse = SSEFormatter.format_node_state("search", "running", "run-1")
        assert "event: node_state" in sse
        assert '"node": "search"' in sse
        assert '"state": "running"' in sse

    def test_format_done(self):
        """Should format done event as SSE."""
        sse = SSEFormatter.format_done("run-1", {"report": {}})
        assert "event: done" in sse
        assert '"type": "done"' in sse

    def test_format_error(self):
        """Should format error event as SSE."""
        sse = SSEFormatter.format_error("Something failed", "run-1")
        assert "event: error" in sse
        assert '"error": "Something failed"' in sse

    def test_format_cancelled(self):
        """Should format cancelled event as SSE."""
        sse = SSEFormatter.format_cancelled("run-1")
        assert "event: cancelled" in sse
        assert '"type": "cancelled"' in sse

    def test_keepalive(self):
        """Should format keepalive."""
        sse = SSEFormatter.keepalive()
        assert sse == ": keepalive\n\n"


class TestProgressTracker:
    """Test progress tracking."""

    def test_hierarchical_progress_mapping(self):
        """Should map hierarchical nodes to progress."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.HIERARCHICAL.value)
        assert tracker.get_progress("prepare_research") == 5
        assert tracker.get_progress("write_report") == 70
        assert tracker.get_progress("finalize_hierarchical") == 100

    def test_debate_progress_mapping(self):
        """Should map debate nodes to progress."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.DEBATE.value)
        assert tracker.get_progress("generate_hypotheses") == 5
        assert tracker.get_progress("cross_examine") == 45
        assert tracker.get_progress("finalize_debate") == 100

    def test_stage_labels_hierarchical(self):
        """Should provide Chinese labels for hierarchical stages."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.HIERARCHICAL.value)
        assert tracker.get_stage_label("prepare_research") == "准备研究"
        assert tracker.get_stage_label("write_report") == "撰写报告"
        assert tracker.get_stage_label("finalize_hierarchical") == "完成"

    def test_stage_labels_debate(self):
        """Should provide Chinese labels for debate stages."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.DEBATE.value)
        assert tracker.get_stage_label("generate_hypotheses") == "生成假设"
        assert tracker.get_stage_label("cross_examine") == "交叉检验"
        assert tracker.get_stage_label("finalize_debate") == "完成"

    def test_debate_branch_labels(self):
        """Should label debate branches dynamically."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.DEBATE.value)
        assert tracker.get_stage_label("support-0") == "辩论-支持 #0"
        assert tracker.get_stage_label("oppose-1") == "辩论-反对 #1"
        assert tracker.get_stage_label("alternative-0") == "辩论-替代 #0"

    def test_progress_info_complete(self):
        """Should return complete progress info."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.HIERARCHICAL.value)
        info = tracker.get_progress_info("write_report", "running")
        assert info["progress"] == 70
        assert info["stage"] == "write_report"
        assert info["stage_label"] == "撰写报告"
        assert info["topology"] == "hierarchical"

    def test_progress_info_terminal(self):
        """Should handle terminal states."""
        tracker = ProgressTracker.for_topology(ResearchStrategy.HIERARCHICAL.value)
        info = tracker.get_progress_info("finalize_hierarchical", "completed")
        assert info["progress"] == 100
        assert info["stage_label"] == "完成"

    def test_unknown_stage(self):
        """Should handle unknown stages gracefully."""
        tracker = ProgressTracker()
        assert tracker.get_stage_label("unknown_node") == "unknown_node"
        assert tracker.get_progress("unknown_node") == 0


class TestResearchRunStreamer:
    """Test research run streamer."""

    @pytest.fixture
    def streamer(self):
        redis_manager = FakeRedisManager()
        event_logger = redis_manager.event_logger()
        publisher = EventPublisher(event_logger)
        return ResearchRunStreamer(publisher)

    @pytest.mark.asyncio
    async def test_stream_run_replays_events(self, streamer):
        """Should replay events for a run."""
        # Publish some events first
        publisher = streamer._publisher
        run_id = "test-run-1"

        await publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.RUN_STARTED,
        )
        await publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.NODE_STARTED,
            node="search",
        )

        events = [e async for e in streamer.stream_run(run_id)]
        assert len(events) >= 2  # At least 2 published + done

    @pytest.mark.asyncio
    async def test_stream_run_includes_done(self, streamer):
        """Should include done event at end."""
        run_id = "test-run-2"
        events = [e async for e in streamer.stream_run(run_id)]
        assert any("done" in e for e in events)


class TestEventJsonSafety:
    """Test event JSON safety."""

    def test_research_event_to_sse(self):
        """ResearchEvent to_sse should produce valid JSON in data field."""
        import json

        event = ResearchEvent(
            event_id="evt-1",
            sequence=1,
            run_id="run-1",
            thread_id="run-1",
            type=EventType.RUN_COMPLETED,
            payload={"terminal_reason": "success"},
        )
        sse = event.to_sse()
        # Parse the data field
        data = json.loads(sse["data"])
        assert data["type"] == "run_completed"
        assert data["payload"]["terminal_reason"] == "success"

    def test_sse_format_contains_all_fields(self):
        """SSE format should contain event, id, data fields."""
        event = ResearchEvent(
            event_id="evt-1",
            sequence=42,
            run_id="run-1",
            thread_id="run-1",
            type=EventType.NODE_STARTED,
            node="analyze",
        )
        sse = SSEFormatter.format_event(event)
        assert "event: node_started" in sse
        assert "id: 42" in sse
        assert "data:" in sse
