from __future__ import annotations

import pytest

from app.model_pool.registry import ModelRegistry
from app.model_pool.router import CapabilityRouter, CostAwareRouter, LatencyRouter
from app.schemas.task import TaskRequirement


@pytest.fixture
def registry() -> ModelRegistry:
    return ModelRegistry()


@pytest.mark.asyncio
async def test_capability_router(registry: ModelRegistry) -> None:
    router = CapabilityRouter(registry)
    req = TaskRequirement(required_capabilities=["web_search_native"])
    model = await router.select_model(req)
    assert model is not None
    assert "web_search_native" in model.capabilities


@pytest.mark.asyncio
async def test_cost_aware_router(registry: ModelRegistry) -> None:
    router = CostAwareRouter(registry)
    req = TaskRequirement(required_capabilities=["strong_reasoning"], preferred_cost_tier="high")
    model = await router.select_model(req)
    assert model is not None
    assert "strong_reasoning" in model.capabilities


@pytest.mark.asyncio
async def test_latency_router(registry: ModelRegistry) -> None:
    router = LatencyRouter(registry)
    req = TaskRequirement(required_capabilities=["web_search_native"])
    model = await router.select_model(req)
    assert model is not None


def test_registry_filter_by_capabilities(registry: ModelRegistry) -> None:
    models = registry.filter_by_capabilities(["strong_reasoning", "writing"])
    assert len(models) > 0
    for m in models:
        assert "strong_reasoning" in m.capabilities
        assert "writing" in m.capabilities


def test_registry_list_enabled(registry: ModelRegistry) -> None:
    models = registry.list_enabled()
    assert len(models) > 0
    for m in models:
        assert m.enabled
