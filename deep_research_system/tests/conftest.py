from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clean_model_env():
    """Ensure MODEL_* env vars are cleared so tests use YAML defaults."""
    keys = [k for k in os.environ if k.startswith("MODEL_")]
    saved = {}
    for k in keys:
        saved[k] = os.environ.pop(k)

    # Also prevent pydantic-settings from reading .env file for these vars
    # by setting them to empty
    for slot in ["SEARCH", "ANALYSIS", "REASONING", "WRITING"]:
        os.environ[f"MODEL_{slot}_NAME"] = ""
        os.environ[f"MODEL_{slot}_API_KEY"] = ""
        os.environ[f"MODEL_{slot}_API_BASE"] = ""

    from app.core.config import reset_config
    reset_config()

    yield

    # Restore
    for slot in ["SEARCH", "ANALYSIS", "REASONING", "WRITING"]:
        os.environ.pop(f"MODEL_{slot}_NAME", None)
        os.environ.pop(f"MODEL_{slot}_API_KEY", None)
        os.environ.pop(f"MODEL_{slot}_API_BASE", None)
    os.environ.update(saved)
    reset_config()
