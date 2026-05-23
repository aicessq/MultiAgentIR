from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.response import success_response
from app.model_pool.key_pool import APIKeyPool
from app.model_pool.registry import ModelRegistry
from app.services.config_service import get_config_service

router = APIRouter(tags=["models"])


class SlotConfigUpdate(BaseModel):
    slot: str
    model_name: str = ""
    api_key: str = ""
    api_base: str = ""


class ModelTestRequest(BaseModel):
    model_name: str
    api_key: str
    api_base: str


@router.get("/models/status")
async def model_status() -> dict:
    registry = ModelRegistry()
    key_pool = APIKeyPool()

    models = []
    for m in registry.list_enabled():
        key_status = key_pool.get_status(m.name)
        models.append({
            "name": m.name,
            "provider": m.provider,
            "capabilities": m.capabilities,
            "cost_tier": m.cost_tier,
            "latency_tier": m.latency_tier,
            "context_window": m.context_window,
            "keys": key_status,
        })

    return success_response({"models": models})


@router.get("/models/config")
async def get_model_config() -> dict:
    svc = await get_config_service()
    slots = await svc.get_all()
    return success_response({"slots": slots})


@router.put("/models/config")
async def update_model_config(updates: list[SlotConfigUpdate]) -> dict:
    svc = await get_config_service()
    for u in updates:
        await svc.update(u.slot, u.model_name, u.api_key, u.api_base)
    slots = await svc.get_all()
    return success_response({"slots": slots, "message": "配置已保存，重启后生效"})


@router.post("/models/test")
async def test_model_connection(req: ModelTestRequest) -> dict:
    import httpx
    try:
        base_url = req.api_base.rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"},
                json={"model": req.model_name, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
            )
            if resp.status_code == 200:
                return success_response({"connected": True, "message": "连接成功"})
            return success_response({"connected": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"})
    except Exception as e:
        return success_response({"connected": False, "message": str(e)[:200]})


@router.post("/models/reset")
async def reset_model_config() -> dict:
    svc = await get_config_service()
    await svc.reset()
    return success_response({"message": "配置已重置"})
