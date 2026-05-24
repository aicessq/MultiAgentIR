from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class KeyStatus(str, Enum):
    HEALTHY = "healthy"
    OPEN = "open"
    HALF_OPEN = "half_open"
    DISABLED = "disabled"


class ModelSpec(BaseModel):
    name: str
    provider: str
    api_base: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    cost_tier: Literal["low", "mid", "high"]
    latency_tier: Literal["fast", "medium", "slow"]
    context_window: int = 8000
    max_tokens: int = 8192
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    enabled: bool = True


class APIKeyConfig(BaseModel):
    key_id: str
    env_name: str
    weight: int = 1


class APIKeyState(BaseModel):
    key_id: str
    status: KeyStatus = KeyStatus.HEALTHY
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    avg_latency_ms: float = 0.0
    weight: int = 1
