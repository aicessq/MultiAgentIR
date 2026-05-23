from __future__ import annotations

import logging

from app.core.config import get_config

logger = logging.getLogger(__name__)


class TopologyRouter:
    def __init__(self) -> None:
        config = get_config()
        self._rules: dict[str, dict] = config.topology.get("routing_rules", {})
        self._default: str = config.topology.get("default_topology", "hierarchical")

    def route(self, task_type: str) -> tuple[str, str]:
        rule = self._rules.get(task_type, {})
        topology = rule.get("topology", self._default)
        writer_template = rule.get("writer_template", "writer/industry_report.zh.j2")
        return topology, writer_template
