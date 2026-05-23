from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Any

from app.schemas.state import ResearchState

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict], Awaitable[None]] | Callable[[dict], None] | None


class BaseTopology(ABC):
    name: str = "base"

    @abstractmethod
    async def execute(self, state: ResearchState, on_event: EventCallback = None) -> ResearchState:
        raise NotImplementedError

    @staticmethod
    def emit(on_event: EventCallback, event: dict) -> None:
        if on_event:
            try:
                result = on_event(event)
                # If it's a coroutine, we can't await here, just fire and forget
                import asyncio
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass
