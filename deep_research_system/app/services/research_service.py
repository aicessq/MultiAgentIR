from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

from app.core.config import get_config
from app.schemas.state import ResearchState
from app.schemas.task import TaskSpec
from app.services.trace_service import TraceService
from app.topology.debate import DebateTopology
from app.topology.hierarchical import HierarchicalTopology
from app.topology.router import TopologyRouter
from app.utils.ids import generate_id
from app.utils.time import now_iso

logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self) -> None:
        self.topology_router = TopologyRouter()
        self._cache: dict[str, Any] = {}  # simple in-memory cache
        self.trace = TraceService()
        self._tasks: dict[str, dict] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._running: dict[str, asyncio.Task] = {}
        self._hierarchical = HierarchicalTopology()
        self._debate = DebateTopology()

    async def initialize(self) -> None:
        pass

    def subscribe(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(task_id, [])
        if queue in subs:
            subs.remove(queue)

    def _emit(self, task_id: str, event: dict) -> None:
        for queue in self._subscribers.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def create_task(self, request: dict) -> dict:
        task_id = generate_id("task")
        task = TaskSpec(task_id=task_id, **request)
        topology_name, writer_template = self.topology_router.route(task.task_type)

        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "progress": 0,
            "current_stage": "init",
            "selected_topology": topology_name,
            "created_at": now_iso(),
            "result": None,
        }

        task_handle = asyncio.create_task(self._execute(task, topology_name, writer_template))
        self._running[task_id] = task_handle
        return self._tasks[task_id]

    async def create_task_sync(self, request: dict) -> dict:
        task_id = generate_id("task")
        task = TaskSpec(task_id=task_id, **request)
        topology_name, writer_template = self.topology_router.route(task.task_type)

        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "progress": 0,
            "current_stage": "init",
            "selected_topology": topology_name,
            "created_at": now_iso(),
            "result": None,
        }

        result = await self._execute(task, topology_name, writer_template)
        return self._tasks[task_id]

    async def _execute(self, task: TaskSpec, topology_name: str, writer_template: str = "writer/industry_report.zh.j2") -> dict:
        task_id = task.task_id
        state = ResearchState(task=task, selected_topology=topology_name, writer_template=writer_template)
        start_time = time.perf_counter()

        def on_topology_event(event: dict) -> None:
            event["task_id"] = task_id
            self._emit(task_id, event)
            # Update task progress
            if "progress" in event:
                self._tasks[task_id]["progress"] = event["progress"]
            if "agent" in event:
                self._tasks[task_id]["current_stage"] = event["agent"]

        try:
            cache_key = hashlib.md5(task.user_query.encode()).hexdigest()
            cached = self._cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for task {task_id}")
                self._tasks[task_id].update({"status": "completed", "progress": 100, "result": cached})
                self._emit(task_id, {"type": "done", "task_id": task_id})
                return cached

            self._emit(task_id, {"type": "start", "topology": topology_name, "progress": 0})

            if topology_name == "debate":
                state = await self._debate.execute(state, on_event=on_topology_event)
            else:
                state = await self._hierarchical.execute(state, on_event=on_topology_event)

            elapsed = (time.perf_counter() - start_time) * 1000

            result = {
                "report": state.final_report,
                "claim_graph": state.claim_graph,
                "metrics": {
                    "cost_so_far": round(state.cost_so_far, 4),
                    "latency_ms": round(elapsed, 2),
                    "model_usage": state.model_usage,
                    "token_usage": state.token_usage,
                    "total_audit_entries": len(state.audit_trail),
                },
                "audit_trail": state.audit_trail,
            }

            self._cache[cache_key] = result
            self.trace.record(task_id, state)

            self._tasks[task_id].update({
                "status": "completed",
                "progress": 100,
                "current_stage": "completed",
                "result": result,
            })

            self._emit(task_id, {
                "type": "done",
                "task_id": task_id,
                "result": result,
                "progress": 100,
                "current_stage": "completed",
            })

            return result

        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
            self._tasks[task_id].update({"status": "cancelled"})
            self._emit(task_id, {"type": "cancelled", "task_id": task_id})
            return {"error": "cancelled"}
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            self._tasks[task_id].update({"status": "failed", "error": str(e)})
            self._emit(task_id, {"type": "error", "task_id": task_id, "error": str(e)})
            return {"error": str(e)}
        finally:
            self._running.pop(task_id, None)

    def get_task(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict]:
        return list(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        task_handle = self._running.get(task_id)
        if task_handle and not task_handle.done():
            task_handle.cancel()
            self._tasks[task_id].update({"status": "cancelled"})
            self._emit(task_id, {"type": "cancelled", "task_id": task_id})
            return True
        return False
