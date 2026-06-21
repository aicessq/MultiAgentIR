from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Terminal states for a research run."""
    QUEUED = "queued"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_QUALITY_GATE = "failed_quality_gate"
    FAILED = "failed"


class ResearchStrategy(str, Enum):
    """Research topology strategy."""
    AUTO = "auto"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"


class TaskSpec(BaseModel):
    task_id: str = ""
    user_query: str
    task_type: Literal[
        "industry_report",
        "company_analysis",
        "technical_research",
        "open_question",
        "strategy_decision",
        "general",
    ] = "general"
    language: str = "zh-CN"
    depth: Literal["quick", "standard", "deep"] = "standard"
    budget_level: Literal["low", "medium", "high"] = "medium"
    max_sources: int = 20
    require_citations: bool = True


class TaskRequirement(BaseModel):
    model_slot: str | None = None  # "search" | "analysis" | "reasoning" | "writing"
    required_capabilities: list[str] = Field(default_factory=list)
    preferred_capabilities: list[str] = Field(default_factory=list)
    preferred_cost_tier: Literal["low", "mid", "high"] = "low"
    max_latency_ms: int | None = None
    complexity: Literal["simple", "medium", "hard"] = "medium"
    min_context_window: int = 8000


class ResearchRequest(BaseModel):
    query: str
    task_type: Literal[
        "industry_report",
        "company_analysis",
        "technical_research",
        "open_question",
        "strategy_decision",
        "general",
    ] = "general"
    depth: Literal["quick", "standard", "deep"] = "standard"
    budget_level: Literal["low", "medium", "high"] = "medium"
    max_sources: int = 20
