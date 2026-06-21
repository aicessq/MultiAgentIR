"""Model request specification for the ModelGateway."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelRequest(BaseModel):
    """Specification for a model call."""

    purpose: str  # e.g., "planner", "analyzer", "writer"
    messages: list[dict] = Field(default_factory=list)
    output_schema_name: str | None = None  # For structured output
    output_schema: dict | None = None  # JSON Schema for validation
    required_capabilities: set[str] = Field(default_factory=set)
    preferred_capabilities: set[str] = Field(default_factory=set)
    max_input_tokens: int | None = None
    max_output_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: float = 60.0
    budget_class: str = "medium"  # "low", "medium", "high"
    stream: bool = False
    max_repair_attempts: int = 2  # Max attempts to repair invalid output


class ModelResponse(BaseModel):
    """Response from a model call."""

    content: str
    parsed_output: dict | None = None  # Validated structured output
    model_name: str
    model_provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    finish_reason: str = "stop"
    repair_attempts: int = 0
    validation_errors: list[str] = Field(default_factory=list)
    raw_response: dict | None = None  # Original API response for debugging


class ModelUsageRecord(BaseModel):
    """Record of model usage for audit."""

    run_id: str
    thread_id: str
    checkpoint_id: str | None = None
    node: str
    namespace: list[str] = Field(default_factory=list)
    subtask_id: str | None = None
    revision_id: str | None = None
    provider: str
    model: str
    attempt: int = 1
    purpose: str
    prompt_version: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    success: bool
    error_category: str | None = None
    error_message: str | None = None
    timestamp: str = Field(default_factory=lambda: "")


class ModelCapability(BaseModel):
    """Capability of a model."""

    name: str
    description: str | None = None
    cost_tier: str = "medium"  # "low", "medium", "high"
    max_context_tokens: int = 8192
    max_output_tokens: int = 4096
    supports_structured_output: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = False
    rate_limit_per_minute: int | None = None
    rate_limit_per_day: int | None = None
    input_cost_per_1k_tokens: float = 0.002
    output_cost_per_1k_tokens: float = 0.006
    enabled: bool = True
    priority: int = 1  # Higher priority = preferred when multiple match


class ModelSpec(BaseModel):
    """Specification of a model provider."""

    name: str
    provider: str
    api_base: str
    api_key_env: str
    model_name: str
    capabilities: list[ModelCapability] = Field(default_factory=list)
    default_capability: ModelCapability | None = None
    enabled: bool = True