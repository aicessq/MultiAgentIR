from __future__ import annotations

from app.core.config import get_config
from app.schemas.model import ModelSpec


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}
        self._slot_map: dict[str, str] = {}  # slot -> model_name
        self._load()

    def _load(self) -> None:
        config = get_config()
        for entry in config.get_effective_models():
            slot = entry.pop("_slot", "")
            spec = ModelSpec(**{k: v for k, v in entry.items() if k in ModelSpec.model_fields})
            self._models[spec.name] = spec
            if slot:
                self._slot_map[slot] = spec.name

    def get(self, name: str) -> ModelSpec | None:
        return self._models.get(name)

    def get_by_slot(self, slot: str) -> ModelSpec | None:
        name = self._slot_map.get(slot)
        return self._models.get(name) if name else None

    def list_all(self) -> list[ModelSpec]:
        return list(self._models.values())

    def list_enabled(self) -> list[ModelSpec]:
        return [m for m in self._models.values() if m.enabled]

    def filter_by_capabilities(self, capabilities: list[str]) -> list[ModelSpec]:
        result = []
        for m in self.list_enabled():
            if all(cap in m.capabilities for cap in capabilities):
                result.append(m)
        return result
