"""EffectiveConfig - frozen configuration for a run.

Key principle: There is only ONE source of truth for runtime configuration.

EffectiveConfig is compiled from:
1. Typed defaults (hardcoded safe defaults)
2. runtime.yaml (project-level settings)
3. Environment secrets/connections (API keys, DB URLs)
4. Optional database overrides (user-specific settings)

Once compiled, it is FROZEN for the duration of the run.
No live config changes affect an in-progress run.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, Field


class GraphConfig(BaseModel):
    """Graph-level configuration."""

    recursion_limit: int = 200
    max_research_rounds: int = 2
    max_report_repairs: int = 2
    max_debate_rounds: int = 2
    interrupt_on_plan_review: bool = False
    interrupt_before_publish: bool = False


class ConcurrencyConfig(BaseModel):
    """Concurrency limits."""

    max_parallel_runs_per_worker: int = 4
    max_parallel_subquestions: int = 4
    search_per_provider: int = 6
    llm_per_provider: int = 4
    fetch_per_host: int = 2


class TimeoutConfig(BaseModel):
    """Timeout settings in seconds."""

    plan_seconds: float = 90.0
    search_seconds: float = 45.0
    fetch_seconds: float = 30.0
    analyze_seconds: float = 180.0
    write_seconds: float = 240.0
    total_run_seconds: float = 1800.0


class BudgetConfig(BaseModel):
    """Budget limits."""

    max_total_tokens: int = 300000
    max_cost_usd: float = 20.0
    warning_ratio: float = 0.8


class QualityConfig(BaseModel):
    """Quality gate settings."""

    pass_score: float = 85.0
    min_evidence_coverage: float = 0.8
    min_source_count: int = 5
    max_empty_sections: int = 0
    require_claim_type: bool = True


class ModelCatalogEntry(BaseModel):
    """A model in the catalog."""

    name: str
    provider: str
    capabilities: list[str] = Field(default_factory=list)
    cost_tier: str = "medium"
    max_context_tokens: int = 8192
    max_output_tokens: int = 4096
    supports_structured_output: bool = False
    enabled: bool = True
    priority: int = 1


class PromptVersion(BaseModel):
    """Prompt version info."""

    agent: str
    purpose: str
    version: str
    path: str
    hash: str


class EffectiveConfig(BaseModel):
    """Frozen configuration for a single run.

    This is the SINGLE source of truth for runtime behavior.
    Created at run start, frozen until run completion.
    """

    # Metadata
    config_snapshot_id: str
    config_hash: str
    compiled_at: datetime = Field(default_factory=datetime.utcnow)
    source_version: str = "v1"  # Config schema version

    # Graph settings
    graph: GraphConfig = Field(default_factory=GraphConfig)

    # Concurrency
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)

    # Timeouts
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)

    # Budget
    budget: BudgetConfig = Field(default_factory=BudgetConfig)

    # Quality
    quality: QualityConfig = Field(default_factory=QualityConfig)

    # Model catalog (frozen snapshot)
    model_catalog: list[ModelCatalogEntry] = Field(default_factory=list)

    # Prompt versions (frozen snapshot)
    prompt_versions: dict[str, PromptVersion] = Field(default_factory=dict)

    # Topology version
    topology_version: str = "v1"

    # Feature flags
    features: dict[str, bool] = Field(default_factory=lambda: {
        "use_structured_output": True,
        "validate_all_outputs": True,
        "track_authoritative_revisions": True,
        "enforce_budget_gates": True,
    })

    def compute_hash(self) -> str:
        """Compute hash of config for verification."""
        serialized = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def get_model_by_capability(self, capability: str) -> list[ModelCatalogEntry]:
        """Get models that have a specific capability."""
        return [
            m for m in self.model_catalog
            if m.enabled and capability in m.capabilities
        ]

    def get_prompt_version(self, agent: str, purpose: str) -> PromptVersion | None:
        """Get prompt version for an agent."""
        key = f"{agent}:{purpose}"
        return self.prompt_versions.get(key)


class ConfigCompiler:
    """Compiles EffectiveConfig from multiple sources.

    Priority order (later overrides earlier):
    1. Typed defaults (hardcoded)
    2. runtime.yaml
    3. Environment variables
    4. Database overrides
    """

    def __init__(
        self,
        defaults: EffectiveConfig | None = None,
        yaml_path: str | None = None,
        env_prefix: str = "RESEARCH_",
    ) -> None:
        self._defaults = defaults or self._create_defaults()
        self._yaml_path = yaml_path
        self._env_prefix = env_prefix

    def compile(
        self,
        yaml_config: dict | None = None,
        env_vars: dict | None = None,
        db_overrides: dict | None = None,
    ) -> EffectiveConfig:
        """Compile EffectiveConfig from all sources."""
        import uuid

        # Start with defaults
        config_dict = self._defaults.model_dump()

        # Apply YAML config
        if yaml_config:
            config_dict = self._merge_dict(config_dict, yaml_config)

        # Apply environment variables
        if env_vars:
            config_dict = self._apply_env_vars(config_dict, env_vars)

        # Apply database overrides
        if db_overrides:
            config_dict = self._merge_dict(config_dict, db_overrides)

        # Create frozen config
        config = EffectiveConfig.model_validate(config_dict)
        config.config_snapshot_id = str(uuid.uuid4())
        config.config_hash = config.compute_hash()

        return config

    def _create_defaults(self) -> EffectiveConfig:
        """Create default configuration."""
        return EffectiveConfig(
            config_snapshot_id="default",
            config_hash="default",
            graph=GraphConfig(),
            concurrency=ConcurrencyConfig(),
            timeout=TimeoutConfig(),
            budget=BudgetConfig(),
            quality=QualityConfig(),
            model_catalog=[
                ModelCatalogEntry(
                    name="deepseek-chat",
                    provider="deepseek",
                    capabilities=["chat", "analysis", "writing"],
                    cost_tier="low",
                    max_context_tokens=64000,
                    max_output_tokens=16384,
                    supports_structured_output=True,
                    enabled=True,
                    priority=1,
                ),
            ],
        )

    def _merge_dict(self, base: dict, override: dict) -> dict:
        """Deep merge two dicts."""
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_vars(self, config_dict: dict, env_vars: dict) -> dict:
        """Apply environment variables to config."""
        # Map env vars to config paths
        env_mapping = {
            "RESEARCH_MAX_TOKENS": ("budget", "max_total_tokens"),
            "RESEARCH_MAX_COST": ("budget", "max_cost_usd"),
            "RESEARCH_TIMEOUT_TOTAL": ("timeout", "total_run_seconds"),
            "RESEARCH_MAX_RESEARCH_LOOPS": ("graph", "max_research_rounds"),
            "RESEARCH_MAX_REPAIRS": ("graph", "max_report_repairs"),
            "RESEARCH_PASS_SCORE": ("quality", "pass_score"),
        }

        for env_key, config_path in env_mapping.items():
            if env_key in env_vars:
                value = env_vars[env_key]
                # Navigate to config location
                section = config_dict
                for path_key in config_path[:-1]:
                    if path_key not in section:
                        section[path_key] = {}
                    section = section[path_key]

                # Set value (convert types as needed)
                final_key = config_path[-1]
                if isinstance(value, str):
                    # Try to convert to appropriate type
                    try:
                        if "tokens" in final_key or "count" in final_key:
                            value = int(value)
                        elif "seconds" in final_key or "score" in final_key or "ratio" in final_key or "cost" in final_key:
                            value = float(value)
                        elif final_key.endswith("_bool") or "enabled" in final_key:
                            value = value.lower() in ("true", "1", "yes")
                    except ValueError:
                        pass

                section[final_key] = value

        return config_dict


class FakeConfigCompiler(ConfigCompiler):
    """Fake compiler for testing."""

    def compile(
        self,
        yaml_config: dict | None = None,
        env_vars: dict | None = None,
        db_overrides: dict | None = None,
    ) -> EffectiveConfig:
        """Return a fixed config for testing."""
        return EffectiveConfig(
            config_snapshot_id="test-config",
            config_hash="test-hash",
            graph=GraphConfig(
                max_research_rounds=1,
                max_report_repairs=1,
            ),
            budget=BudgetConfig(
                max_total_tokens=100000,
                max_cost_usd=5.0,
            ),
        )