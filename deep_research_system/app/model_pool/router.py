from __future__ import annotations

import logging

from app.model_pool.key_pool import APIKeyPool
from app.model_pool.registry import ModelRegistry
from app.schemas.model import ModelSpec
from app.schemas.task import TaskRequirement

logger = logging.getLogger(__name__)

COST_RANK = {"low": 0, "mid": 1, "high": 2}
LATENCY_RANK = {"fast": 0, "medium": 1, "slow": 2}


class BaseRouter:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    async def select_model(self, requirement: TaskRequirement) -> ModelSpec | None:
        raise NotImplementedError


class CapabilityRouter(BaseRouter):
    async def select_model(self, requirement: TaskRequirement) -> ModelSpec | None:
        candidates = self.registry.filter_by_capabilities(requirement.required_capabilities)
        if not candidates:
            logger.warning(f"No model satisfies capabilities: {requirement.required_capabilities}")
            candidates = self.registry.list_enabled()
        return candidates[0] if candidates else None


class CostAwareRouter(BaseRouter):
    async def select_model(self, requirement: TaskRequirement) -> ModelSpec | None:
        candidates = self.registry.filter_by_capabilities(requirement.required_capabilities)
        if not candidates:
            candidates = self.registry.list_enabled()
        if not candidates:
            return None
        preferred = [m for m in candidates if m.cost_tier == requirement.preferred_cost_tier]
        if preferred:
            return min(preferred, key=lambda m: LATENCY_RANK.get(m.latency_tier, 1))
        return min(candidates, key=lambda m: COST_RANK.get(m.cost_tier, 1))


class LatencyRouter(BaseRouter):
    async def select_model(self, requirement: TaskRequirement) -> ModelSpec | None:
        candidates = self.registry.filter_by_capabilities(requirement.required_capabilities)
        if not candidates:
            candidates = self.registry.list_enabled()
        if not candidates:
            return None
        return min(candidates, key=lambda m: LATENCY_RANK.get(m.latency_tier, 1))


class FallbackRouter(BaseRouter):
    def __init__(self, registry: ModelRegistry, key_pool: APIKeyPool | None = None) -> None:
        super().__init__(registry)
        self.key_pool = key_pool
        self._chain: list[BaseRouter] = [
            CostAwareRouter(registry),
            CapabilityRouter(registry),
            LatencyRouter(registry),
        ]

    async def select_model(self, requirement: TaskRequirement) -> ModelSpec | None:
        for router in self._chain:
            model = await router.select_model(requirement)
            if model:
                return model
        return None
