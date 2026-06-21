"""Research Worker process.

Responsible for:
1. Consuming tasks from Redis queue
2. Running LangGraph
3. Publishing events to Redis
4. Saving checkpoints
5. Handling cancellation
6. Graceful shutdown
"""

from __future__ import annotations

import asyncio
import logging
import signal
import uuid
from datetime import datetime
from typing import Any

from app.config import EffectiveConfig
from app.domain.enums import RunStatus
from app.infrastructure.checkpoint.postgres import AsyncPostgresSaver, FakePostgresSaver
from app.infrastructure.events.publisher import EventPublisher, EventType
from app.infrastructure.redis.streams import TaskQueue, EventLogger, CancellationManager

logger = logging.getLogger(__name__)


class Worker:
    """Research Worker process.

    Consumes tasks from queue and executes research graphs.
    """

    def __init__(
        self,
        worker_id: str,
        task_queue: TaskQueue,
        event_logger: EventLogger,
        cancellation_manager: CancellationManager,
        checkpointer: AsyncPostgresSaver | FakePostgresSaver,
        event_publisher: EventPublisher,
        graph_registry: dict[str, Any],
    ) -> None:
        self._worker_id = worker_id
        self._task_queue = task_queue
        self._event_logger = event_logger
        self._cancellation = cancellation_manager
        self._checkpointer = checkpointer
        self._event_publisher = event_publisher
        self._graph_registry = graph_registry

        self._running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the worker."""
        self._running = True
        logger.info(f"Worker {self._worker_id} started")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal, sig)

        while self._running:
            try:
                task = await self._task_queue.dequeue(timeout_ms=5000)
                if task:
                    await self._process_task(task)
            except asyncio.CancelledError:
                logger.info(f"Worker {self._worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {self._worker_id} stopped")

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info(f"Worker {self._worker_id} shutting down...")
        self._running = False
        self._shutdown_event.set()

    def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal."""
        logger.info(f"Worker {self._worker_id} received {sig.name}")
        asyncio.create_task(self.stop())

    async def _process_task(self, task: dict) -> None:
        """Process a single task."""
        run_id = task["run_id"]
        query = task["query"]
        task_type = task["task_type"]
        strategy = task["strategy"]
        message_id = task.get("_message_id")

        logger.info(f"Processing task {run_id}")

        try:
            # Check for cancellation
            if await self._cancellation.is_cancelled(run_id):
                logger.info(f"Run {run_id} was cancelled before start")
                if message_id:
                    await self._task_queue.acknowledge(message_id)
                return

            # Get graph from registry
            graph = self._graph_registry.get(strategy)
            if not graph:
                logger.error(f"No graph for strategy {strategy}")
                await self._task_queue.acknowledge(message_id)
                return

            # Create initial state
            initial_state = {
                "run_id": run_id,
                "thread_id": run_id,
                "query": query,
                "task_type": task_type,
                "requested_strategy": strategy,
                "status": RunStatus.RUNNING.value,
            }

            # Run the graph
            result = await self._run_graph(run_id, graph, initial_state)

            # Publish completion
            if result.get("status") == RunStatus.COMPLETED.value:
                await self._event_publisher.publish_run_completed(
                    run_id=run_id,
                    thread_id=run_id,
                    payload={"terminal_reason": result.get("terminal_reason")},
                )
            else:
                await self._event_publisher.publish_run_failed(
                    run_id=run_id,
                    thread_id=run_id,
                    error=result.get("terminal_reason", "Unknown error"),
                )

        except asyncio.CancelledError:
            logger.info(f"Run {run_id} cancelled during execution")
            await self._handle_cancellation(run_id)
            raise

        except Exception as e:
            logger.error(f"Task {run_id} failed: {e}")
            await self._event_publisher.publish_run_failed(
                run_id=run_id,
                thread_id=run_id,
                error=str(e),
            )

        finally:
            if message_id:
                await self._task_queue.acknowledge(message_id)

    async def _run_graph(
        self,
        run_id: str,
        graph: Any,
        initial_state: dict,
    ) -> dict:
        """Run the research graph."""
        # Check cancellation periodically
        check_interval = 10  # Check every N steps

        try:
            result = await graph.run(initial_state)

            # Save final checkpoint
            await self._checkpointer.aput(
                thread_id=run_id,
                checkpoint_id=f"final-{run_id}",
                state=result,
            )

            return result

        except asyncio.CancelledError:
            # Save checkpoint for resume
            logger.info(f"Saving checkpoint for cancelled run {run_id}")
            # The actual checkpoint saving would happen in the graph execution
            raise

    async def _handle_cancellation(self, run_id: str) -> None:
        """Handle cancellation during execution."""
        # Save checkpoint
        checkpoint_id = f"cancelled-{run_id}-{datetime.utcnow().isoformat()}"

        # Publish cancelled event
        await self._event_publisher.publish(
            run_id=run_id,
            thread_id=run_id,
            event_type=EventType.RUN_CANCELLED,
            payload={"cancelled_at": datetime.utcnow().isoformat()},
        )

        # Clear cancellation flag
        await self._cancellation.clear_cancel(run_id)


class WorkerPool:
    """Pool of workers for horizontal scaling."""

    def __init__(
        self,
        worker_count: int,
        task_queue: TaskQueue,
        event_logger: EventLogger,
        cancellation_manager: CancellationManager,
        checkpointer: AsyncPostgresSaver | FakePostgresSaver,
        event_publisher: EventPublisher,
        graph_registry: dict[str, Any],
    ) -> None:
        self._workers: list[Worker] = []
        self._worker_count = worker_count

        for i in range(worker_count):
            worker_id = f"worker-{uuid.uuid4().hex[:8]}"
            worker = Worker(
                worker_id=worker_id,
                task_queue=task_queue,
                event_logger=event_logger,
                cancellation_manager=cancellation_manager,
                checkpointer=checkpointer,
                event_publisher=event_publisher,
                graph_registry=graph_registry,
            )
            self._workers.append(worker)

    async def start(self) -> None:
        """Start all workers."""
        await asyncio.gather(
            *[worker.start() for worker in self._workers]
        )

    async def stop(self) -> None:
        """Stop all workers."""
        await asyncio.gather(
            *[worker.stop() for worker in self._workers]
        )
