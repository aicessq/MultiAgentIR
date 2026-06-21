from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.task import TaskSpec


def merge_unique_strings(existing: list[str], updates: list[str]) -> list[str]:
    """Merge two lists, keeping only unique items, preserving order."""
    result = list(existing)
    for item in updates:
        if item not in result:
            result.append(item)
    return result


def merge_dict(existing: dict, updates: dict) -> dict:
    """Merge two dicts, with updates taking precedence."""
    return {**existing, **updates}


def append_list(existing: list[dict], updates: list[dict]) -> list[dict]:
    """Append new items to existing list."""
    return existing + updates


class ResearchState(BaseModel):
    task: TaskSpec
    selected_strategy: Literal["hierarchical", "debate"] | None = None
    writer_template: str = "writer/industry_report.zh.j2"
    plan: list[dict] = []
    sub_results: dict[str, dict] = {}
    debate_results: dict[str, dict] = {}
    analyses: list[dict] = Field(default_factory=list)

    # Authoritative revision pointers (Phase 0 requirement)
    authoritative_analysis_id: str | None = None
    authoritative_critique_id: str | None = None

    critiques: list[dict] = Field(default_factory=list)
    final_report: dict | None = None

    # Evidence protocol fields
    source_registry: dict[str, dict] = Field(default_factory=dict)  # url -> SearchSource dict
    claim_graph: list[dict] = Field(default_factory=list)  # AnalyzerClaim dicts
    claim_audit: list[dict] = Field(default_factory=list)
    repair_context: list[dict] = Field(default_factory=list)

    cost_so_far: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})
    model_usage: dict[str, int] = {}
    audit_trail: list[dict] = []
    errors: list[dict] = []

    current_stage: str = ""
    progress: int = 0

    # Config snapshot tracking (Phase 0 requirement)
    config_snapshot_id: str | None = None
    config_hash: str | None = None

    # Research loops tracking
    research_round: int = 0
    max_research_rounds: int = 2
    repair_count: int = 0
    max_repairs: int = 2

    # Budget tracking
    budget: dict[str, float] = Field(default_factory=lambda: {
        "max_total_tokens": 300000,
        "max_cost_usd": 20.0,
        "warning_ratio": 0.8,
    })
    usage: dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})

    # Terminal state
    terminal_reason: str | None = None

    def add_audit(self, agent: str, model: str, prompt_version: str, token_in: int, token_out: int, cost: float, latency_ms: float) -> None:
        self.audit_trail.append({
            "agent": agent,
            "model": model,
            "prompt_version": prompt_version,
            "token_in": token_in,
            "token_out": token_out,
            "cost": cost,
            "latency_ms": latency_ms,
        })
        self.cost_so_far += cost
        self.token_usage["prompt_tokens"] = self.token_usage.get("prompt_tokens", 0) + token_in
        self.token_usage["completion_tokens"] = self.token_usage.get("completion_tokens", 0) + token_out
        self.model_usage[model] = self.model_usage.get(model, 0) + 1
