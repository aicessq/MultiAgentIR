"""Seed config utility - validates and displays loaded configuration."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_config
from app.model_pool.registry import ModelRegistry
from app.topology.router import TopologyRouter


def main() -> None:
    config = get_config()

    print("=== Models ===")
    registry = ModelRegistry()
    for m in registry.list_enabled():
        print(f"  {m.name} ({m.provider}) - caps: {m.capabilities}")

    print(f"\n=== Agents ===")
    for name, cfg in config.agents.get("agents", {}).items():
        print(f"  {name}: caps={cfg.get('required_capabilities')}, template={cfg.get('prompt_template')}")

    print(f"\n=== Topology Routing ===")
    router = TopologyRouter()
    for task_type in ["industry_report", "company_analysis", "open_question", "strategy_decision", "general"]:
        topo, template = router.route(task_type)
        print(f"  {task_type} -> {topo} (template: {template})")


if __name__ == "__main__":
    main()
