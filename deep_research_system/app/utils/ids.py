from __future__ import annotations

import uuid


def generate_id(prefix: str = "task") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def generate_key_id() -> str:
    return uuid.uuid4().hex[:8]
