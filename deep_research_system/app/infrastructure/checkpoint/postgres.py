"""AsyncPostgresSaver for LangGraph checkpointing.

This implements the checkpointer interface for PostgreSQL.
thread_id = run_id for our use case.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import Column, String, JSON, DateTime, select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.infrastructure.db.base import Base

logger = logging.getLogger(__name__)


class CheckpointRecord(Base):
    """Checkpoint record for LangGraph state."""

    __tablename__ = "checkpoints"

    thread_id = Column(String(64), primary_key=True)  # run_id
    checkpoint_id = Column(String(64), primary_key=True)
    parent_checkpoint_id = Column(String(64), nullable=True)

    state = Column(JSON, nullable=False)
    checkpoint_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)


class AsyncPostgresSaver:
    """Async PostgreSQL checkpointer for LangGraph.

    Usage:
        saver = AsyncPostgresSaver(session_factory)
        graph = builder.compile(checkpointer=saver)
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        thread_id_key: str = "run_id",
    ) -> None:
        self._session_factory = session_factory
        self._thread_id_key = thread_id_key

    async def aget(self, thread_id: str) -> dict | None:
        """Get the latest checkpoint for a thread."""
        async with self._session_factory() as session:
            stmt = (
                select(CheckpointRecord)
                .where(CheckpointRecord.thread_id == thread_id)
                .order_by(CheckpointRecord.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                return {
                    "checkpoint_id": record.checkpoint_id,
                    "parent_checkpoint_id": record.parent_checkpoint_id,
                    "state": record.state,
                    "metadata": record.checkpoint_metadata,
                }
            return None

    async def alist(
        self,
        thread_id: str,
        limit: int = 100,
    ) -> AsyncIterator[dict]:
        """List checkpoints for a thread, newest first."""
        async with self._session_factory() as session:
            stmt = (
                select(CheckpointRecord)
                .where(CheckpointRecord.thread_id == thread_id)
                .order_by(CheckpointRecord.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            for record in result.scalars():
                yield {
                    "checkpoint_id": record.checkpoint_id,
                    "parent_checkpoint_id": record.parent_checkpoint_id,
                    "state": record.state,
                    "metadata": record.checkpoint_metadata,
                }

    async def aput(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: dict,
        parent_checkpoint_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Put a checkpoint."""
        async with self._session_factory() as session:
            record = CheckpointRecord(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                parent_checkpoint_id=parent_checkpoint_id,
                state=state,
                checkpoint_metadata=metadata or {},
            )
            session.add(record)
            await session.commit()

    async def adelete(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread."""
        async with self._session_factory() as session:
            await session.execute(
                delete(CheckpointRecord).where(CheckpointRecord.thread_id == thread_id)
            )
            await session.commit()

    async def aget_next_version(
        self,
        thread_id: str,
        checkpoint_id: str,
    ) -> str:
        """Get the next version ID for a checkpoint."""
        async with self._session_factory() as session:
            stmt = (
                select(CheckpointRecord)
                .where(CheckpointRecord.thread_id == thread_id)
                .order_by(CheckpointRecord.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                # Extract version from checkpoint_id
                parts = checkpoint_id.split(".")
                if len(parts) >= 2:
                    version = int(parts[-1]) + 1
                    return ".".join(parts[:-1]) + f".{version}"
            return f"{checkpoint_id}.1"


class FakePostgresSaver:
    """Fake checkpointer for testing."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, list[dict]] = {}

    async def aget(self, thread_id: str) -> dict | None:
        checkpoints = self._checkpoints.get(thread_id, [])
        return checkpoints[-1] if checkpoints else None

    async def alist(self, thread_id: str, limit: int = 100) -> AsyncIterator[dict]:
        checkpoints = self._checkpoints.get(thread_id, [])
        for checkpoint in checkpoints[-limit:]:  # oldest first within limit
            yield checkpoint

    async def aput(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: dict,
        parent_checkpoint_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        if thread_id not in self._checkpoints:
            self._checkpoints[thread_id] = []
        self._checkpoints[thread_id].append({
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "state": state,
            "metadata": metadata or {},
        })

    async def adelete(self, thread_id: str) -> None:
        self._checkpoints.pop(thread_id, None)

    async def aget_next_version(
        self,
        thread_id: str,
        checkpoint_id: str,
    ) -> str:
        return f"{checkpoint_id}.1"
