from __future__ import annotations

import os

from app.core.config import get_config
from app.model_pool.circuit_breaker import KeyCircuitBreaker
from app.schemas.model import APIKeyConfig, APIKeyState, KeyStatus


class APIKeyPool:
    def __init__(self) -> None:
        self._keys: dict[str, list[APIKeyConfig]] = {}
        self._states: dict[str, APIKeyState] = {}
        self._circuit_breaker = KeyCircuitBreaker()
        self._current_index: dict[str, int] = {}
        self._slot_key_env: dict[str, str] = {}  # model_name -> env_name
        self._load()

    def _load(self) -> None:
        config = get_config()
        # 从 env 或 YAML 加载 key 配置
        for model_name, keys in config.get_effective_api_keys().items():
            self._keys[model_name] = []
            for k in keys:
                kc = APIKeyConfig(**k)
                self._keys[model_name].append(kc)
                self._states[kc.key_id] = APIKeyState(key_id=kc.key_id, weight=kc.weight)
                # 记录 model_name -> env_name 映射
                self._slot_key_env[model_name] = kc.env_name

    def get_api_key(self, model_name: str) -> str | None:
        config = get_config()
        keys = self._keys.get(model_name, [])
        if keys:
            idx = self._current_index.get(model_name, 0)
            for _ in range(len(keys)):
                kc = keys[idx % len(keys)]
                status = self._circuit_breaker.get_status(kc.key_id)
                if status in (KeyStatus.HEALTHY, KeyStatus.HALF_OPEN):
                    self._current_index[model_name] = (idx + 1) % len(keys)
                    # 1. Try provider-based env var (e.g. QWEN_API_KEY)
                    val = os.getenv(kc.env_name, "")
                    if val:
                        return val
                    # 2. Try Settings attributes (e.g. settings.QWEN_API_KEY)
                    val = getattr(config.settings, kc.env_name, "")
                    if val:
                        return val
                idx += 1

        # fallback: try all slot-based env vars (MODEL_SEARCH_API_KEY, etc.)
        for slot in ["search", "analysis", "reasoning", "writing"]:
            val = os.getenv(f"MODEL_{slot.upper()}_API_KEY", "")
            if val:
                return val

        return None

    def record_success(self, key_id: str) -> None:
        self._circuit_breaker.record_success(key_id)
        state = self._states.get(key_id)
        if state:
            state.success_count += 1
            state.total_calls += 1

    def record_failure(self, key_id: str) -> None:
        self._circuit_breaker.record_failure(key_id)
        state = self._states.get(key_id)
        if state:
            state.failure_count += 1
            state.total_calls += 1

    def get_status(self, model_name: str) -> list[dict]:
        keys = self._keys.get(model_name, [])
        result = []
        for kc in keys:
            state = self._states.get(kc.key_id)
            status = self._circuit_breaker.get_status(kc.key_id)
            result.append({
                "key_id": kc.key_id,
                "status": status.value,
                "success_count": state.success_count if state else 0,
                "failure_count": state.failure_count if state else 0,
                "total_calls": state.total_calls if state else 0,
            })
        return result
