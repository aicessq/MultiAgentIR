from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.task import TaskSpec


class ResearchState(BaseModel):
    task: TaskSpec
    selected_topology: str | None = None
    writer_template: str = "writer/industry_report.zh.j2"
    plan: list[dict] = []
    sub_results: dict[str, dict] = {}
    debate_results: dict[str, dict] = {}
    analyses: list[dict] = []
    critiques: list[dict] = []
    final_report: dict | None = None

    # Evidence protocol fields
    source_registry: dict[str, dict] = Field(default_factory=dict)  # url -> SearchSource dict
    claim_graph: list[dict] = Field(default_factory=list)  # AnalyzerClaim dicts
    claim_audit: list[dict] = Field(default_factory=list)

    cost_so_far: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})
    model_usage: dict[str, int] = {}
    audit_trail: list[dict] = []
    errors: list[dict] = []

    current_stage: str = ""
    progress: int = 0

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
